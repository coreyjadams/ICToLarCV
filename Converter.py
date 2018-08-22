import os, sys
import numpy

from IOManager import IOManager
from ROOT import larcv
import ROOT
import load_db
from ParticleConverter import ParticleConverter


class Converter(object):

    def __init__(self):
        super(Converter, self).__init__()

        # Pointers to the files:
        self._input_file  = None
        self._output_file = None

        # IO Instances:
        self._larcv_io = None
        self._next_io  = None

        self._initialized = False

        self._pc = ParticleConverter()

    def convert(self, _file_in, _file_out = None, max_entries = None):

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

        self.event_loop(max_entries = max_entries)

    def initialize_geometry(self):
        '''Set up and cache the geometry information

        Creates meta objects for larcv and reads the database for h5.
        '''

        # Read in the database to get the pmt and sipm locations:
        self._pmt_locations  = load_db.DataPMT()
        self._sipm_locations = load_db.DataSiPM()
        self._det_geo        = load_db.DetectorGeo()

        min_x = numpy.min(self._sipm_locations.X)
        max_x = numpy.max(self._sipm_locations.X)
        min_y = numpy.min(self._sipm_locations.Y)
        max_y = numpy.max(self._sipm_locations.Y)
        min_z = self._det_geo.ZMIN
        max_z = self._det_geo.ZMAX

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
        hits        = self._next_io.mc().hits(self._event)
        particles   = self._next_io.mc().particles(self._event)
        larcv_particle_set = self._larcv_io.get_data("particle",  "mcpart")
        larcv_voxel3d      = self._larcv_io.get_data("sparse3d",  "mcpart")
        larcv_cluster3d    = self._larcv_io.get_data("cluster3d", "mcpart")
        larcv_particle_set.clear()
        larcv_voxel3d.clear()
        larcv_cluster3d.clear()


        larcv_voxel3d.meta(self._mc_meta)
        larcv_cluster3d.meta(self._mc_meta)


        particle_index_mapping = dict()
        i = 0
        for particle in particles:
            larcv_particle = larcv.Particle()
            larcv_particle.id(i)
            larcv_particle.track_id(int(particle['particle_indx']))
            particle_index_mapping[particle['particle_indx']] = i
            larcv_particle.parent_track_id(int(particle['mother_indx']))
            larcv_particle.pdg_code(self._pc.get_pdg(particles[i]['particle_name']))
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
            larcv_voxel3d.emplace(xyz[0], xyz[1],xyz[2], hit['hit_energy'])
            # Get the particle index of this hit:
            if hit['particle_indx'] in particle_index_mapping.keys():
                idx = particle_index_mapping[int(hit['particle_indx'])]
            else:
                idx = i
            larcv_voxel_index = self._mc_meta.id(xyz[0],xyz[1],xyz[2])
            voxel = larcv.Voxel(larcv_voxel_index, hit['hit_energy'])
            larcv_cluster3d.writeable_voxel_set(idx).add(voxel)


        return True


    def convert_pmaps(self):

        print "Converting pmaps"

        if self._larcv_io is None:
            raise Exception("No larcv IO manager found.")

        if self._next_io is None:
            raise Exception("No next IO manager found.")


        pmaps = self._next_io.pmaps()
        larcv_voxel = self._larcv_io.get_data("sparse3d", "pmaps")
        larcv_voxel.clear()
        larcv_voxel.meta(self._pmaps_meta)

        larcv_meta = self._larcv_io.get_data("meta", "pmaps")

        # Get the sipms location
        _sipm_locations = load_db.DataSiPM()


        print "Got all data"

        # Use S1 to get t0
        if pmaps.s1() is None:
            return False
        if pmaps.s2Pmt() is None:
            return False
        if pmaps.s2Si() is None:
            return False

        s1_peak_time_idx = numpy.argmax(numpy.asarray(pmaps.s1()['ene']))
        t0 = pmaps.s1()['time'][s1_peak_time_idx]
        t0 *= 1e-3


        # Covert the S2 df to a dictionary
        s2_dict = {}

        for i in xrange(0, len(pmaps.s2())):
            current_peak = s2_dict.setdefault(pmaps.s2()['peak'][i], ([], []))
            current_peak[0].append(pmaps.s2()['time'][i])
            current_peak[1].append(pmaps.s2()['ene'][i])


        print "s2 converted to dict"
        # print 's2_dict', s2_dict


        # Covert the S2Si df to a dictionary
        # s2si_dict is a dictionary {peak number, sipms dictionary}
        # 'sipms dictionary' is a dictionary {sipms number, time and energy arrays}
        s2si_dict = {}

        print len(pmaps.s2Si())

        for i in xrange(0, len(pmaps.s2Si())):

            peak_number = pmaps.s2Si()['peak'][i]
            sipm_number = pmaps.s2Si()['nsipm'][i]

            current_peak  = s2si_dict.setdefault   (peak_number, {}      )
            current_sipms = current_peak.setdefault(sipm_number, ([], []))

            # Get the time from previous S2 dictionary, and save time and energy
            e = pmaps.s2Si()['ene'][i]
            t = s2_dict[peak_number][0][len(current_sipms[0])]
            current_sipms[0].append(t)
            current_sipms[1].append(e)

            x = self._sipm_locations.X[sipm_number]
            y = self._sipm_locations.Y[sipm_number]
            z = 1e-3*t - t0

            if e > 0.00001:
                larcv_voxel.emplace(x, y, z, e)


        print "s2si saved"
        # Covert the S2PMT df to a dictionary
        # s2pmt_dict is a dictionary {peak number, pmt dictionary}
        # 'pmt dictionary' is a dictionary {pmt number, time and energy arrays}
        s2pmt_dict = {}

        times = ROOT.std.vector('double')()
        energies = ROOT.std.vector('double')()

        for i in xrange(0, len(pmaps.s2Pmt())):

            peak_number = pmaps.s2Pmt()['peak'][i]
            pmt_number = pmaps.s2Pmt()['npmt'][i]

            current_peak  = s2pmt_dict.setdefault  (peak_number, {}      )
            current_pmts  = current_peak.setdefault(pmt_number,  ([], []))

            # Get the time from previous S2 dictionary, and save time and energy
            e = pmaps.s2Pmt()['ene'][i]
            t = s2_dict[peak_number][0][len(current_pmts[0])]
            current_pmts[0].append(t)
            current_pmts[1].append(e)

            times.push_back(t)
            energies.push_back(e)

        larcv_meta.store("s2pmt_time", times)
        larcv_meta.store("s2pmt_energy", energies)

        print "Finished converting pmaps"

        return True


    def event_loop(self, max_entries=None):

        if not self._initialized:
            raise Exception("Need to initialize before event loop.")

        entry_count = 0
        for entry in self._next_io.entries():

            print entry

            if entry_count % 1 == 0:
                sys.stdout.write("Processed entry {}.\n".format(entry_count))

            # Read the entry in the next IO:
            self._next_io.go_to_entry(entry)

            self._entry = entry
            self._event = self._next_io.event()
            self._run = self._next_io.run()

            if self._run < 0:
                self._run = 0

            ##########################
            # Do the conversions here.
            ##########################
            _ok = self.convert_mc_information()
            _ok = self.convert_pmaps() and _ok

            print _ok


            if _ok:
                self._larcv_io.set_id(int(self._run), 0, int(self._event))
                self._larcv_io.save_entry()
                entry_count += 1

            if max_entries is not None and entry > max_entries:
                break

        self._larcv_io.finalize()

        sys.stdout.write("Total number of entries converted: {}\n".format(entry_count))
