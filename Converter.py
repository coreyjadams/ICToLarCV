import os
import numpy

from IOManager import IOManager
from ROOT import larcv
import load_db
from ParticleConverter import ParticleConverter


class Converter(object):

    def __init__(self):
        super(self, Converter).__init__()

        # Pointers to the files:
        self._input_file  = None
        self._output_file = None

        # IO Instances:
        self._larcv_io = None
        self._next_io  = None

        self._initialized = False

        self._pc = ParticleConverter()

    def convert(self, _file_in, _file_out = None):

        # if there is not an output file, the output is the input with a new file extension:
        if _file_out is None:
            directory = os.path.dirname(_file_in)
            file_root = os.path.basename(_file_in)
            _file_out = directory + os.path.splitext(file_root)[0] + '_larcv.root'
            # print _file_out

        self._input_file  = _file_in
        self._output_file = _file_out

        if not self._initialized:
            self.initialize_geometry()
            self._initialized = True

        # Create the instances of IO managers:
        self._next_io =  IOManager()
        self._next_io.set_file(self._input_file)

        # larcv io:
        self._larcv_io = larcv.IOManager(larcv.IOManager.kWRITE)
        self._larcv_io.set_out_file(self._output_file)
        self._larcv_io.initialize()

        self.event_loop()

    def initialize_geometry(self):
        '''Set up and cache the geometry information

        Creates meta objects for larcv and reads the database for h5.
        '''

        # Read in the database to get the pmt and sipm locations:
        self.pmt_locations  = load_db.DataPMT()
        self.sipm_locations = load_db.DataSiPM()
        self.det_geo        = load_db.DetectorGeo()

        min_x = numpy.min(self.sipm_locations.X)
        max_x = numpy.max(self.sipm_locations.X)
        min_y = numpy.min(self.sipm_locations.Y)
        max_y = numpy.max(self.sipm_locations.Y)
        min_z = self.det_geo.ZMIN
        max_z = self.det_geo.ZMAX

        n_x = int(max_x - min_x)
        n_y = int(max_y - min_y)
        n_z = int(max_z - min_z)

        # Create just one meta to use for NEXT-New
        self._mc_meta = larcv.Voxel3DMeta()
        self._mc_meta.set(min_x, min_y, min_z,
                          max_x, max_y, max_z,
                          n_x, n_y, n_z)


        n_x = n_x / 10
        n_y = n_y / 10

        self._pmaps_meta = larcv.Voxel3DMeta()
        self._pmaps_meta.set(min_x, min_y, min_z,
                             max_x, max_y, max_z,
                             n_x, n_y, n_z)

        return

    def convert_mc_information(self):

        if self._larcv_io is None:
            raise Exception("No larcv IO manager found.")

        if self._next_io is None:
            raise Exception("No next IO manager found.")

        # Convert particle object
        hits        = self._next_io.mc().hits(event)
        particles   = self._next_io.mc().particles(event)
        larcv_particle = self._larcv_io.get_data("particle",  "mcpart")
        larcv_voxel    = self._larcv_io.get_data("sparse3d",  "mcpart")
        larcv_cluster  = self._larcv_io.get_data("cluster3d", "mcpart")
        larcv_voxel.meta(self._mc_meta)
        larcv_cluster.meta(self._mc_meta)


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
            # Momentum:
            larcv_particle.momentum(particle['momentum'][0], particle['momentum'][1], particle['momentum'][2])
            #kinetic energy:
            larcv_particle.energy_init(particle['kin_energy'])
            larcv_particle.creation_process(particle['creator_proc'])

            larcv_particle_set.append(larcv_particle)
            i += 1;
            # print particle

        # Create a set of clusters to match the length of the particles:
        larcv_cluster3d.resize(i + 1)

        for hit in hits:
            xyz = hit['hit_position']
            larcv_voxel.emplace(xyz[0], xyz[1],xyz[2], hit['hit_energy'])
            # Get the particle index of this hit:
            if hit['particle_indx'] in particle_index_mapping.keys():
                idx = particle_index_mapping[int(hit['particle_indx'])]
            else:
                idx = i
            larcv_voxel_index = meta.id(xyz[0],xyz[1],xyz[2])
            voxel = larcv.Voxel(larcv_voxel_index, hit['hit_energy'])
            larcv_cluster.writeable_voxel_set(idx).add(voxel)




    def convert_pmaps(self):

        if self._larcv_io is None:
            raise Exception("No larcv IO manager found.")

        if self._next_io is None:
            raise Exception("No next IO manager found.")


        pmaps = next_io.pmaps()
        larcv_voxel = larcv_io.get_data("sparse3d", "pmaps")
        larcv_voxel.meta(pmaps_meta)


    def event_loop(self, max_entries = None):

        if not self._initialized:
            raise Exception("Need to initialize before event loop.")


        for entry in self._next_io.entries():

            # Read the entry in the next IO:
            self._next_io.go_to_entry(entry)

            event = self._next_io.event()
            run = self._next_io.run()

            if run < 0:
                run = 0

            ##########################
            # Do the conversions here.
            ##########################
            self.convert_mc_information()
            self.convert_pmaps()




            larcv_io.set_id(int(run), 0, int(event))
            larcv_io.save_entry()

            if max_entries is not None and entry > max_entries:
                break

        larcv_io.finalize()


def save_pmaps(pmaps, larcv_voxel, meta):

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

def get_meta(pmaps=False):


if __name__ == '__main__':
    convert_file("nexus_ACTIVE_10bar_EPEM_detsim.next_10000.root.diomira.irene.h5")
