import os

from IOManager import IOManager
from ROOT import larcv


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

    # Create just one meta to use for NEXT-New
    meta = larcv.Voxel3DMeta()

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
        larcv_particle = larcv_io.get_data("particle", 'mcpart')

        save_mc(hits, particles, larcv_particle)

        larcv_io.set_id(int(run), 0, int(event))
        larcv_io.save_entry()
        break

    larcv_io.finalize()

def save_mc(hits, particles, larcv_particle):

    print "Number of particles: "  + str(len(particles))
    print "Number of hits: " + str(len(hits))

    print particles.dtype
    print hits.dtype

    particle = larcv.Particle()

    larcv_particle.append(particle)


if __name__ == '__main__':
    convert_file("nexus_ACTIVE_10bar_EPEM_detsim.next_10000.root.diomira.irene.h5")

