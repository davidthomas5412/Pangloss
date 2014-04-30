#!/usr/bin/env python
# ======================================================================

import pangloss

import sys,getopt,cPickle,numpy
import matplotlib.pyplot as plt


# ======================================================================

def Reconstruct(argv):
    """
    NAME
        Reconstruct.py

    PURPOSE
        Read in a simulation lightcone (or list of lightcones) and compute all 
        quantities needed to estimate kappah, the convergence due to
        halos, at the centre of the lightcone. Output is a list of sample
        kappah values drawn from Pr(kappah|D), where D refers to either 
        observed data, or simulated data from a calibration line of
        sight.

    COMMENTS
        The config file contains the list of lightcones to be
        reconstructed, in the form of either a directory or a single
        instance. If a directory is specified, one also gives a number
        ("batchsize") of lightcones to be reconstructed at a time. 
        The number of kappah samples desired must also be given in the
        config file.

    FLAGS
        -h            Print this message [0]

    INPUTS
        configfile    Plain text file containing Pangloss configuration

    OUTPUTS
        stdout        Useful information
        samples       Catalog(s) of samples from Pr(kappah|D)

    EXAMPLE
        Reconstruct.py example.config

    BUGS
        - Code is incomplete.

    AUTHORS
      This file is part of the Pangloss project, distributed under the
      GPL v2, by Tom Collett (IoA) and  Phil Marshall (Oxford). 
      Please cite: Collett et al 2013, http://arxiv.org/abs/1303.6564

    HISTORY
      2013-03-21 started Collett & Marshall (Oxford)
    """

    # --------------------------------------------------------------------

    try:
       opts, args = getopt.getopt(argv,"h",["help"])
    except getopt.GetoptError, err:
       print str(err) # will print something like "option -a not recognized"
       print Reconstruct.__doc__  # will print the big comment above.
       return

    for o,a in opts:
       if o in ("-h", "--help"):
          print Reconstruct.__doc__
          return
       else:
          assert False, "unhandled option"

    # Check for setup file in array args:
    if len(args) == 1:
        configfile = args[0]
        print pangloss.doubledashedline
        print pangloss.hello
        print pangloss.doubledashedline
        print "Reconstruct: assigning halo mass to various lightcones"
        print "Reconstruct: taking instructions from",configfile
    else:
        print Reconstruct.__doc__
        return

    # --------------------------------------------------------------------
    # Read in configuration, and extract the ones we need:
    
    experiment = pangloss.Configuration(configfile)

    # Get the experiment name from the configfile name instead?
    EXP_NAME = experiment.parameters['ExperimentName']

    zd = experiment.parameters['StrongLensRedshift']
    zs = experiment.parameters['SourceRedshift']

    calpickles = []
    Nc = experiment.parameters['NCalibrationLightcones']
    for i in range(Nc):
        calpickles.append(experiment.getLightconePickleName('simulated',pointing=i))
    
    obspickle = experiment.getLightconePickleName('real')
    
    # Ray tracing:
    RTscheme = experiment.parameters['RayTracingScheme']
    
    # SHM relation parameters:
    SHMrelation = experiment.parameters['StellarMass2HaloMassRelation']
    CALIB_DIR = experiment.parameters['CalibrationFolder'][0]
    SHMfile = CALIB_DIR+'/'+SHMrelation+'.pickle'
    
    # Halo mass function data:
    HMFfile = experiment.parameters['HMFfile'][0]
    
    # Photo-zs:
    zperr = experiment.parameters['PhotozError']
    
    # Stellar mass observations:
    MserrP = experiment.parameters['PhotometricMstarError']
    MserrS = experiment.parameters['SpectroscopicMstarError']
    # Sampling Pr(kappah|D):
    Ns = experiment.parameters['NRealisations']
    
    # Reconstruct calibration lines of sight?
    DoCal = experiment.parameters['ReconstructCalibrations']

    # --------------------------------------------------------------------
    # Load in stellar mass to halo relation, or make a new one:

    try:
        shmr = pangloss.readPickle('dummy')#SHMfile)
    except IOError:
        print "Reconstruct: generating the stellar mass to halo mass grid."
        print "Reconstruct: this may take a moment..."
        shmr = pangloss.SHMR(method=SHMrelation)
        shmr.makeHaloMassFunction(HMFfile)
        shmr.makeCDFs()
        pangloss.writePickle(shmr,SHMfile)
        print "Reconstruct: SHMR saved to "+SHMfile
    
    # --------------------------------------------------------------------
    # Make redshift grid:
    
    grid = pangloss.Grid(zd,zs,nplanes=100)
    
    # --------------------------------------------------------------------
    # Read in lightcones from pickles:

    calcones = []
    for i in range(Nc):
        calcones.append(pangloss.readPickle(calpickles[i]))
    obscone = pangloss.readPickle(obspickle)
    if DoCal=="False": #must be string type
        calcones=[]
        calpickles=[]

    allcones = calcones#+[obscone]
    allconefiles = calpickles#+[obspickle]   
    
    # --------------------------------------------------------------------
    # Make realisations of each lightcone, and store sample kappah vals:
    pk = pangloss.PDF('kappa_halo')
    pmu = pangloss.PDF('mu_halo')
    for i in range(len(allcones)):

        print pangloss.dashedline
        print "Reconstruct: drawing %i samples from Pr(kappah|D)" % (Ns)
        print "Reconstruct:   given data in "+allconefiles[i]

        # Get lightcone, and start PDF for its kappa_halo:
        lc = allcones[i]
       # pk = pangloss.PDF('kappa_halo')
       # pmu = pangloss.PDF('mu_halo')

        # coming soon: gamma1, gamma2...

        # Redshift scaffolding:
        lc.defineSystem(zd,zs)
        lc.loadGrid(grid)

        # Figure out data quality etc:
        lc.configureForSurvey(experiment)

        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

        # Draw Ns sample realisations of this lightcone, and hence
        # accumulate samples from Pr(kappah|D):
        for j in range(Ns):

            if j % 20 == 0 and j !=0:
                print ("Reconstruct: ...on sample %i out of %i..." % (j,Ns))

            # Draw z from z_obs:
            #lc.mimicPhotozError(sigma=zperr)
            lc.snapToGrid(grid)
            
            # Simulated lightcones need mock observed Mstar_obs values 
            # drawing from their Mhalos:
            #if lc.flavor == 'simulated': lc.drawMstars(shmr)
            
            # Draw Mstar from Mstar_obs:
            #lc.mimicMstarError(sigmaP=MserrP,sigmaS=MserrS)

            # Draw Mhalo from Mstar, and then c from Mhalo:
            #lc.drawMhalos(shmr)
            lc.drawConcentrations(errors=True)

            # Compute each halo's contribution to the convergence:
            lc.makeKappas(truncationscale=10)
            
            k_add=lc.combineKappas()

            mu_add=lc.combineMus()

            pmu.append([lc.mu_add_total])

            if RTscheme == 'sum':
                pk.append([lc.kappa_add_total])
                # coming soon: lc.gamma1_add_total, lc.gamma2_add_total
            elif RTscheme == 'keeton':
                pk.append([lc.kappa_keeton])
            else:
                raise "Unknown ray-tracing scheme: "+RTscheme
            
            # Make a nice visualisation of one of the realisations, in
            # two example cases:
            if j ==0 and (lc.flavor == 'real' or i == 0):
                x = allconefiles[i]
                pngfile = x.split('.')[0]
                lc.plot('kappa', output=pngfile+"_kappa.png")
                lc.plot('mu', output=pngfile+"_mu.png")

                print "Reconstruct: saved visualisation of lightcone in "+pngfile
        
        

        
        """# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        # Plot mu vs z
        
        redshift = lc.galaxies.z
        magnification = lc.galaxies.mu
        
        z_bins = numpy.linspace(0, 3.5, 8)
        
        def find_index(z,zl,zu):
           
            Finds the indices of all elements in array that are within given
            redshift range
            
            ind = numpy.transpose(numpy.nonzero((z >= zl) & (z <= zu)))
            return ind
        

        K=lc.galaxies.kappa
        G1=lc.galaxies.gamma1
        G2=lc.galaxies.gamma2
            
        Ksum = numpy.sum(K)
        G1sum = numpy.sum(G1)
        G2sum = numpy.sum(G2)
        Gsum = numpy.sqrt(G1sum**2 + G2sum**2)
            
        total_Msum = 1.0/(((1.0 - Ksum)**2.0) - (Gsum**2.0))
        
        Musum=[]
        z_mid=[]
        for j in range(len(z_bins)-1):
            zrange = find_index(redshift, z_bins[j], z_bins[j+1])
            zmid = 0.5 * (z_bins[j]+z_bins[j+1])
            subset = zrange[:,0]
            mu_subset = magnification[subset]
            K=lc.galaxies.kappa[subset]
            G1=lc.galaxies.gamma1[subset]
            G2=lc.galaxies.gamma2[subset]
            
            Ksum = numpy.sum(K)
            G1sum = numpy.sum(G1)
            G2sum = numpy.sum(G2)
            Gsum = numpy.sqrt(G1sum**2 + G2sum**2)
            
            Msum = 1.0/(((1.0 - Ksum)**2.0) - (Gsum**2.0))
            Musum.append(Msum)
            z_mid.append(zmid)

        plt.clf()
        plt.bar(z_mid, Musum/total_Msum, 0.35, color='g', align='center', alpha=0.4)
        plt.xlabel(r'Redshift, $z$', fontsize=16)
        plt.ylabel(r'Magnification, $\mu$', fontsize=16)
        plt.title(r'Distribution of Magnification')
        plt.savefig('mu_z_prob.png',dpi=300,bbox_inches='tight')

        plt.show()
        """                
        # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 


        # Take Hilbert ray-traced kappa for this lightcone as "truth":
        pk.truth[0] = lc.kappa_hilbert
        
        # Pickle this lightcone's PDF:
        x = allconefiles[i]
        pfile = x.split('.')[0].split("_lightcone")[0]+"_"+EXP_NAME+"_PofKappah.pickle"
        pangloss.writePickle(pk,pfile)

        print "Reconstruct: Pr(kappah|D) saved to "+pfile
        
        # To save loading in time in Calibrate.py we compute the median
        # of kappah and save it in a separate file, with kappaHilbert
        if lc.flavor=="simulated":
            pfile2 = x.split('.')[0].split("_lightcone")[0]+"_"+EXP_NAME+"_KappaHilbert_Kappah_median.pickle"
            pangloss.writePickle([pk.truth[0],[numpy.median(pk.samples)]],pfile2)

            # BUG: shouldn't Pr(kappa,<kappah>) be pickled as a PDF?
            # BUG: and named appropriately? 
            # No, this is just a pair of values

        #print numpy.median(p.samples)
    # --------------------------------------------------------------------
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    # Plot p(mu) histogram
        
    pmu.plot('mu_halo',output="pofmu.png")
    pk.plot('kappa_halo',output="pofkappa.png")
    
    
    print pangloss.doubledashedline
    return

# ======================================================================

if __name__ == '__main__': 
    Reconstruct(sys.argv[1:])

# ======================================================================
