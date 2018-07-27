import os

import numpy

import h5py

class MCReader(object):

    def __init__(self, mc_group):
        super(MCReader, self).__init__()
        self._group = mc_group

        # Read the extents:
        self._extents = self._group['extents']

        # The list of events is in the extents table:
        self._events    = self._extents['evt_number']
        self._hits      = self._group['hits']
        self._particles = self._group['particles']
        self._n_entries = len(self._events)

    def events(self, event):
        return events

    def entry_from_event(self, event):
        try:
            return numpy.where(self._events == event)[0][0]
        except:
            raise Exception("Event {} not found in the file".format(event))

    def hits(self, event):

        entry = self.entry_from_event(event)

        if entry == 0:
            min_hit = 0
        else:
            min_hit = int(self._extents[entry-1]['last_hit'] + 1)

        max_hit = int(self._extents[entry]['last_hit'])

        # Get the slice of hits:
        hits = self._hits[min_hit:max_hit]
        return hits

    def particles(self,event):

        entry = self.entry_from_event(event)

        if entry == 0:
            min_particle = 0
        else:
            min_particle = int(self._extents[entry-1]['last_particle'] + 1)

        max_particle = int(self._extents[entry]['last_particle'])

        # Get the slice of hits:
        particles = self._particles[min_particle:max_particle]
        return particles


class PMapsReader(object):

    def __init__(self, pmaps_group):
        super(PMapsReader, self).__init__()
        self._group = pmaps_group

        self._s1    = self._group['S1']
        self._s1Pmt = self._group['S1Pmt']
        self._s2    = self._group['S2']
        self._s2Pmt = self._group['S2Pmt']
        self._s2Si  = self._group['S2Si']
        self._event = None

    def s1(self, event=None):

        if event is None:
            event = self._event

        # Make a slice of the s1 object:
        indexes = numpy.where(self._s1['event'] == event)[0]
        if len(indexes) == 0:
            return None
        else:
            min_index = numpy.min(indexes)
            max_index = numpy.max(indexes) + 1
            # This is a basic contiguiousness check (sp?  how do you spell that?)
            assert len(indexes) == max_index - min_index
            return self._s1[min_index:max_index]


    def s1Pmt(self, event=None):

        if event is None:
            event = self._event

        # Make a slice of the s1 object:
        indexes = numpy.where(self._s1Pmt['event'] == event)[0]
        if len(indexes) == 0:
            return None
        else:
            min_index = numpy.min(indexes)
            max_index = numpy.max(indexes) + 1
            # This is a basic contiguiousness check (sp?  how do you spell that?)
            assert len(indexes) == max_index - min_index
            return self._s1Pmt[min_index:max_index]

    def s2(self, event=None):

        if event is None:
            event = self._event

        # Make a slice of the s1 object:
        indexes = numpy.where(self._s2['event'] == event)[0]
        if len(indexes) == 0:
            return None
        else:
            min_index = numpy.min(indexes)
            max_index = numpy.max(indexes) + 1
            # continuity assertion:
            assert len(indexes) == max_index - min_index
            return self._s2[min_index:max_index]


    def s2Pmt(self, event=None):

        if event is None:
            event = self._event

        # Make a slice of the s1 object:
        indexes = numpy.where(self._s2Pmt['event'] == event)[0]
        if len(indexes) == 0:
            return None
        else:
            min_index = numpy.min(indexes)
            max_index = numpy.max(indexes) + 1
            # continuity assertion:
            assert len(indexes) == max_index - min_index
            return self._s2Pmt[min_index:max_index]

    def s2Si(self, event=None):

        if event is None:
            event = self._event

        # Make a slice of the s1 object:
        indexes = numpy.where(self._s2Si['event'] == event)[0]
        if len(indexes) == 0:
            return None
        else:
            min_index = numpy.min(indexes)
            max_index = numpy.max(indexes) + 1
            # continuity assertion:
            assert len(indexes) == max_index - min_index
            return self._s2Si[min_index:max_index]




class IOManager(object):
    """wrapper to IC event interface to allow random access through events

    IC doesn't implicitly allow a random access event loop.  This class
    reads an entire file into memory, and then stores the events to allow
    the event viewer to access them randomly.
    """
    def __init__(self):
        super(IOManager, self).__init__()


        # Current entry in the above list
        self._current_entry = 0
        self._file = None
        self._mc = None
        self._pmaps = None
        self._events = None

    def event(self):
        """Get the data from the current event

        Returns:
            [type] -- [description]
        """
        return self._events['evt_number'][self._current_entry]

    def entry(self):
        """Get the currently accessed entry

        Returns:
            int -- the active entry
        """
        return self._current_entry

    def entries(self):
        return self._entries

    def run(self):
        """Get the run number of the current entry

        Returns:
            int -- the current run number
        """
        return self._runs['run_number'][self._current_entry]

    def timestamp(self):
        """Get the timestamp for the current entry

        Returns:
            timestamp
        """
        return self._events['timestamp'][self._current_entry]


    def set_file(self, file_name):
        """Open a new file and read it's data

        Read the pmaps from a new file.  Will attempt to read MC as well, though
        it will catch exceptions if any MC is missing.

        Does not yet read reconstructed information, this is a TODO

        Arguments:
            file_name {str} -- path to file to open
        """

        self._file = h5py.File(file_name, 'r')


        self._runs = self._file['Run']['runInfo']
        self._events = self._file['Run']['events']

        self._current_entry = 0
        self._max_entry = len(self._events)
        self._entries = numpy.arange(0, self._max_entry)


        self._mc = MCReader(self._file['MC'])
        self._pmaps = PMapsReader(self._file['PMAPS'])


    def pmaps(self):
        """Return the pmap object for selected entry

        If event is specified explicitly, check event is available and return that s2
        Otherwise, return s2 for currently active event

        Keyword Arguments:
            entry {number} -- [event number] (default: {-1})

        Returns:
            PMap - evm.Pmap object
        """

        return self._pmaps


    def mc(self):
        """Return mchit objects

        If event is specified explicitly, check event is available and return that mchits
        Otherwise, return mchis for currently active event

        Keyword Arguments:
            event {number} -- [description] (default: {-1})

        Returns:
            mchits -- MCHits object
        """


        return self._mc


    def num_events(self):
        """Query for the total number of events in this file

        Returns:
            int -- Total number of events
        """
        return _max_entry

    def go_to_entry(self,entry):
        """Move the current index to the specified entry

        Move the access point to the entry specified.  Does checks to
        verify the entry is available.

        Arguments:
            entry {int} -- Desired entry
        """

        if entry in self._entries:
            self._current_entry = entry
            self._pmaps._event = self.event()
        else:
            print("Can't go to entry {}, entry is out of range.".format(entry))


