import os
import numpy

from IOManager import IOManager
from ROOT import larcv
import load_db
from ParticleConverter import ParticleConverter


def convert_file(input_file, output_file=None):

    # if there is not an output file, the output is the input with a new file extension:
    if output_file is None:
        directory = os.path.dirname(input_file)
        file_root = os.path.basename(input_file)
        output_file = directory + os.path.splitext(file_root)[0] + '_larcv.root'
        print output_file


    next_io = IOManager()
    next_io.set_file(input_file)

    # larcv io:
    larcv_io = larcv.IOManager(larcv.IOManager.kWRITE)
    larcv_io.set_out_file(output_file)
    larcv_io.initialize()


    meta = get_meta()


    for entry in next_io.entries():
        # do some conversion
        next_io.go_to_entry(entry)
        event = next_io.event()
        run = next_io.run()

        if run < 0:
            run = 0

        ##########################
        # Do the conversions here.
        ##########################

        # Convert particle object
        hits = next_io.mc().hits(event)
        particles = next_io.mc().particles(event)
        larcv_particle = larcv_io.get_data("particle",  "mcpart")
        larcv_voxel    = larcv_io.get_data("sparse3d",  "mcpart")
        larcv_cluster  = larcv_io.get_data("cluster3d", "mcpart")
        larcv_voxel.meta(meta)
        larcv_cluster.meta(meta)
        save_mc(hits, particles, larcv_particle, larcv_cluster, larcv_voxel, meta)

        pmaps = next_io.pmaps()
        larcv_voxel = larcv_io.get_data("sparse3d", "pmaps")
        larcv_voxel.meta(meta)
        save_pmaps(pmaps, larcv_voxel, meta)


        larcv_io.set_id(int(run), 0, int(event))
        larcv_io.save_entry()
        break

    larcv_io.finalize()

def save_mc(hits, particles, larcv_particle_set, larcv_cluster3d, larcv_voxel3d, meta):

    print "Number of particles: "  + str(len(particles))
    print "Number of hits: " + str(len(hits))

    pc = ParticleConverter()

    print particles.dtype
    particle_index_mapping = dict()
    i = 0
    for particle in particles:
        larcv_particle = larcv.Particle()
        larcv_particle.id(i)
        larcv_particle.track_id(int(particle['particle_indx']))
        particle_index_mapping[particle['particle_indx']] = i
        larcv_particle.parent_track_id(int(particle['mother_indx']))
        larcv_particle.pdg_code(pc.get_pdg(particles[i]['particle_name']))
        larcv_particle.position(particle['initial_vertex'][0], particle['initial_vertex'][1], particle['initial_vertex'][2], particle['initial_vertex'][3])
        larcv_particle.end_position(particle['final_vertex'][0], particle['final_vertex'][1], particle['final_vertex'][2], particle['final_vertex'][3])
        larcv_particle_set.append(larcv_particle)
        i += 1;
        # print particle

    print particle_index_mapping
    # Create a set of clusters to match the length of the particles:
    larcv_cluster3d.resize(i + 1)


    print hits.dtype

    for hit in hits:
        xyz = hit['hit_position']
        larcv_voxel3d.emplace(xyz[0], xyz[1],xyz[2], hit['hit_energy'])
        # Get the particle index of this hit:
        if hit['particle_indx'] in particle_index_mapping.keys():
            idx = particle_index_mapping[int(hit['particle_indx'])]
        else:
            idx = i
        larcv_voxel_index = meta.id(xyz[0],xyz[1],xyz[2])
        voxel = larcv.Voxel(larcv_voxel_index, hit['hit_energy'])
        larcv_cluster3d.writeable_voxel_set(idx).add(voxel)


def save_pmaps(pmaps, larcv_voxel, meta):

    # print pmaps.s1()
    # print pmaps.s2()
    # print pmaps.s1Pmt()
    # print pmaps.s2Pmt()
    # print pmaps.s2Si()

    # The code that parses pmaps for visualization is here:
    # https://github.com/coreyjadams/IC/blob/master/invisible_cities/viewer/datatypes/PMap.py#L80-L89

    # A lot of the functions there are not implemented for the hacked IO of the hdf5 files
    # We will have to figure them out


    # Get the sipms location
    sipm_locations = load_db.DataSiPM()


    # Use S1 to get t0
    print len(pmaps.s1())
    s1_peak_time_idx = numpy.argmax(numpy.asarray(pmaps.s1()['ene']))
    t0 = numpy.asarray(pmaps.s1()['time'])[s1_peak_time_idx]
    t0 *= 1e-3

    
    # Covert the S2 df to a dictionary
    s2_dict = {}

    for i in xrange(0, len(pmaps.s2())):
        current_peak = s2_dict.setdefault(pmaps.s2()['peak'][i], ([], []))
        current_peak[0].append(pmaps.s2()['time'][i])
        current_peak[1].append(pmaps.s2()['ene'][i])


    # print 's2_dict', s2_dict
    print 'Number of peaks', len(s2_dict)

    
    # Covert the S2Si df to a dictionary
    # s2si_dict is a dictionary {peak number, sipms dictionary}
    # 'sipms dictionary' is a dictionary {sipms number, time and energy arrays}
    s2si_dict = {}

    for i in xrange(0, len(pmaps.s2Si())):

        peak_number = pmaps.s2Si()['peak'][i]
        sipm_number = pmaps.s2Si()['nsipm'][i]

        current_peak  = s2si_dict.setdefault   (peak_number, {}      )
        current_sipms = current_peak.setdefault(sipm_number, ([], []))

        # Get the time from previous S2 dictionary, and save time and energy
        t = s2_dict[peak_number][0][len(current_sipms[0])]
        e = pmaps.s2Si()['ene'][i]
        current_sipms[0].append(t)
        current_sipms[1].append(e)

        x = sipm_locations.X[sipm_number]
        y = sipm_locations.Y[sipm_number]
        z = 1e-3*t - t0

        larcv_voxel.emplace(x, y, z, e)




    

    # # Loop over peaks, then sipms, then time ticks
    # # For each time tick create a voxel
    # for peak in s2_dict:
    #     for sipm in s2si_dict[peak]:
    #         for t, e in zip(s2si_dict[peak][sipm][0], s2si_dict[peak][sipm][1]):
    #             x = sipm_locations.X[sipm]
    #             y = sipm_locations.Y[sipm]
    #             z = 1e-3*t - t0
    #             # print 'sipm location', x, y, z
    #             larcv_voxel.emplace(x, y, z, e)


    # larcv_voxel.emplace(x=1,y=2,z=3,val=4)
    # larcv_voxel.emplace(1,2,3,4)

    return

def get_meta():

    # Read in the database to get the pmt and sipm locations:
    pmt_locations = load_db.DataPMT()
    sipm_locations = load_db.DataSiPM()
    det_geo = load_db.DetectorGeo()

    min_x = numpy.min(sipm_locations.X)
    max_x = numpy.max(sipm_locations.X)
    min_y = numpy.min(sipm_locations.Y)
    max_y = numpy.max(sipm_locations.Y)
    min_z = det_geo.ZMIN
    max_z = det_geo.ZMAX

    n_x = int(max_x - min_x)
    n_y = int(max_y - min_y)
    n_z = int(max_z - min_z)

    # Create just one meta to use for NEXT-New
    meta = larcv.Voxel3DMeta()
    meta.set(min_x,
             min_y,
             min_z,
             max_x,
             max_y,
             max_z,
             n_x,
             n_y,
             n_z)


    return meta

if __name__ == '__main__':
    convert_file("nexus_ACTIVE_10bar_EPEM_detsim.next_10000.root.diomira.irene.h5")

