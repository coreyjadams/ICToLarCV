class ParticleConverter(object):
    """Coverts particle names to pdg code
    """
    def __init__(self):
        super(ParticleConverter, self).__init__()


        # Default value
        self._default = -999


    def get_pdg(self, particle_name):
        """Get PDG number associated with particle name

        Returns:
            [type] -- [description]
        """
        if (particle_name == "e+"):    return -11
        if (particle_name == "e-"):    return +11
        if (particle_name == "gamma"): return +22
        else:                          return self._default

