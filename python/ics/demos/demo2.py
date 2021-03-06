"""

This example demonstrates how to use the collisions simulation code with the
most recent calibration data.

"""

import pathlib
import time
import numpy as np

from ics.cobraCharmer.pfiDesign import PFIDesign
from ics.cobraOps import plotUtils
from ics.cobraOps import targetUtils
from ics.cobraOps.Bench import Bench
from ics.cobraOps.CollisionSimulator import CollisionSimulator
from ics.cobraOps.DistanceTargetSelector import DistanceTargetSelector
from ics.cobraOps.RandomTargetSelector import RandomTargetSelector

# Define the target density to use
targetDensity = 1.5

# Get the calibration product from the pfs_instdata repository
calibrationProduct = PFIDesign(pathlib.Path(
    "/home/jgracia/github/pfs_instdata/data/pfi/modules/ALL/ALL_final_20210512.xml"))

# Transform the calibration product cobra centers and link lengths units from
# pixels to millimeters
calibrationProduct.centers -= 5048.0 + 3597.0j
calibrationProduct.centers *= np.exp(1j * np.deg2rad(1.0)) / 13.02
calibrationProduct.L1 /= 13.02
calibrationProduct.L2 /= 13.02

# Use the median value link lengths in those cobras with zero link lengths
zeroLinkLengths = np.logical_or(
    calibrationProduct.L1 == 0, calibrationProduct.L2 == 0)
calibrationProduct.L1[zeroLinkLengths] = np.median(
    calibrationProduct.L1[~zeroLinkLengths])
calibrationProduct.L2[zeroLinkLengths] = np.median(
    calibrationProduct.L2[~zeroLinkLengths])

# Use the median value link lengths in those cobras with too long link lengths
tooLongLinkLengths = np.logical_or(
    calibrationProduct.L1 > 100, calibrationProduct.L2 > 100)
calibrationProduct.L1[tooLongLinkLengths] = np.median(
    calibrationProduct.L1[~tooLongLinkLengths])
calibrationProduct.L2[tooLongLinkLengths] = np.median(
    calibrationProduct.L2[~tooLongLinkLengths])

# Create the bench instance
bench = Bench(layout="full", calibrationProduct=calibrationProduct)
print("Number of cobras:", bench.cobras.nCobras)

# Generate the targets
targets = targetUtils.generateRandomTargets(targetDensity, bench)
print("Number of simulated targets:", targets.nTargets)

# Select the targets
selector = DistanceTargetSelector(bench, targets)
selector.run()
selectedTargets = selector.getSelectedTargets()

# Simulate an observation
start = time.time()
simulator = CollisionSimulator(bench, selectedTargets, trajectorySteps=450)
simulator.run()
print("Number of cobras involved in collisions:", simulator.nCollisions)
print("Number of cobras unaffected by end collisions: ",
      simulator.nCollisions - simulator.nEndPointCollisions)
print("Total simulation time (s):", time.time() - start)

# Plot the simulation results
simulator.plotResults(extraTargets=targets, paintFootprints=False)

# Animate one of the trajectory collisions
(problematicCobras,) = np.where(
    np.logical_and(simulator.collisions, simulator.endPointCollisions == False))

if len(problematicCobras) > 0:
    simulator.animateCobraTrajectory(problematicCobras[0], extraTargets=targets)

# Pause the execution to have time to inspect the figures
plotUtils.pauseExecution()
