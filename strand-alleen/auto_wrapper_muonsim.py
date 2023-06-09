#!/usr/bin/env python
import aa, ROOT
from ROOT import EventFile, Det, cxx, TH1D, Timer, time_at
import muonsim
from muonsim import residual_map
import numpy as np

#infile = "/sps/km3net/repo/data_processing/tag/v8.1/data_processing/prod/mc/atm_muon/KM3NeT_00000133/v8.1/reco/mcv8.1.mupage_tuned_100G.sirene.jterbr00013754.jchain.aashower.3094.root" #simulated tracks
#infile = "/sps/km3net/repo/data_processing/tag/v8.1/data_processing/prod/data/KM3NeT_00000133/v8.1.1/reco/datav8.1.1.jchain.aashower.00013754.root" #real data
aashower_startno = 137
aashower_midno = 50
infile_real = []
for i in range(0, 10):
    infile_real.append("/sps/km3net/repo/data_processing/tag/v8.1/data_processing/prod/data/KM3NeT_00000133/v8.1.1/reco/datav8.1.1.jchain.aashower.000%i%i.root" %(aashower_startno, aashower_midno + i))

infile_sim = []
sim_path = "/sps/km3net/repo/data_processing/tag/v8.1/data_processing/prod/mc/atm_muon/KM3NeT_00000133/v8.1/reco/"
with open("output.txt") as file:
    for line in file:
        infile_sim.append(sim_path + line)


for i,n in enumerate(infile_sim):
    infile_sim[i] = n.strip()

f = EventFile( infile_sim )


rmap = residual_map()

notrack = 0

for evt in f :

    try :
        trk = ROOT.get_best_reconstructed_jppmuon( evt )
    except ROOT.Exception: 
        notrack+=1
        continue

    rmap.fill( evt.hits, trk )


print (notrack,"out of", f.size(),"events had no track")
print()
print ("the following doms have at least one hit ")
print()
print (list(rmap.domids()))
print()

no_pmts = 31
hit_array = np.zeros([len(list(rmap.domids())),no_pmts,  3])
#Note structure as follows and note that pmts without hits are excluded 
#dom-ids / pmt no / no-hits 
domid_map = list(rmap.domids())
print("test if the map is working properly")
lowerbound, upperbound = -50, 60
#lowerbound, upperbound = -50, 150

for j in range(0, len(domid_map)):
    """Structure as follows: [dom number, pmt-number, amount of hits]"""
    for i in range(0, 31):
        hit_array[j, i, 0] = domid_map[j]
        hit_array[j, i, 1] = i
        hit_array[j, i, 2] = rmap.geth(domid_map[j], i).Integral(lowerbound,upperbound)

np.save("muon_hit_data_sim-001375x.npy", hit_array)
