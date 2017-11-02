"""

Some utility methods related with the science targets.

Consult the following papers for more detailed information:

  http://adsabs.harvard.edu/abs/2012SPIE.8450E..17F
  http://adsabs.harvard.edu/abs/2014SPIE.9151E..1YF
  http://adsabs.harvard.edu/abs/2016arXiv160801075T

"""

import numpy as np

import ics.cobraOps.benchUtils as benchUtils
import ics.cobraOps.plotUtils as plotUtils


NULL_TARGET_INDEX = -1
"""Integer value used to indicate that there is no target index associated with
a given cobra."""


def generateTargets(density, bench):
    """Generates a set of targets uniformly distributed over the bench field of
    view.

    Parameters
    ----------
    density: float
        The average number of targets per patrol area.
    bench: object
        The bench geometry to use.

    Returns
    -------
    Object
        Complex numpy array with the targets positions.

    """
    # Calculate the total number of targets based on the bench properties
    benchCenter = np.mean(bench["center"])
    benchRadius = np.max(np.abs(bench["center"] - benchCenter) + bench["rMax"])
    medianPatrolRadius = np.median(bench["rMax"])
    nTargets = int(np.ceil(density * (benchRadius / medianPatrolRadius) ** 2))
 
    # Calculate the uniformly distributed target positions
    ang = 2 * np.pi * np.random.random(nTargets)
    radius = benchRadius * np.sqrt(np.random.random(nTargets)) 
    targetPositions = radius * np.exp(1j * ang)

    # Move the targets positions to the bench central position
    targetPositions += benchCenter

    return targetPositions


def assignTargets(targetPositions, bench):
    """Assigns a set of targets to the cobras in the bench.

    Parameters
    ----------
    targetPositions: object
        A complex numpy array with the targets coordinates.
    bench: object
        The bench geometry to use.
    
    Returns
    -------
    tuple
        A python tuple with the assigned target indices and the final fiber
        positions.

    """
    # Get the indices and distances of those targets that can be reached by
    # each cobra
    (targetIndices, targetDistances) = getAccesibleTargets(targetPositions, bench)
    
    # Assign a single target to each cobra based of the target distances
    assignedTargets = assignTargetsByDistance(targetIndices, targetDistances)
   
    # Calculate the fiber final positions solving possible collisions between
    # cobras
    fiberPositions = solveCobraCollisions(assignedTargets, targetIndices, targetPositions, bench)

    return (assignedTargets, fiberPositions)


def getAccesibleTargets(targetPositions, bench):
    """Returns the targets that each cobra can reach ordered by distance.

    Parameters
    ----------
    targetPositions: object
        A complex numpy array with the targets coordinates.
    bench: object
        The bench geometry to use.
    
    Returns
    -------
    tuple
        A python tuple with the indices and distances of each target that can
        be reached by the cobra.

    """
    # Obtain the cobra-target associations: select first by the x axis 
    # distance and then by the y axis distance
    xDistanceMatrix = np.abs(bench["center"].real[:, np.newaxis] - targetPositions.real)
    (cobras, targets) = np.where(xDistanceMatrix < bench["rMax"][:, np.newaxis])
    yDistance = np.abs(bench["center"][cobras].imag - targetPositions[targets].imag)
    validIndices = yDistance < bench["rMax"][cobras]
    cobras = cobras[validIndices]
    targets = targets[validIndices]
    
    # Select only those targets that can be reached by each cobra
    distances = np.abs(bench["center"][cobras] - targetPositions[targets])
    validIndices = np.logical_and(distances > bench["rMin"][cobras], distances < bench["rMax"][cobras])
    cobras = cobras[validIndices]
    targets = targets[validIndices]
    distances = distances[validIndices]

    # Calculate the total number of targets that each cobra can reach
    nTargetsPerCobra = np.bincount(cobras)
    
    # Order the targets by their distance to the cobra
    nCobras = len(bench["center"])
    maxTagetsPerCobra = nTargetsPerCobra.max()
    targetIndices = np.full((nCobras, maxTagetsPerCobra), NULL_TARGET_INDEX, dtype="int")
    targetDistances = np.zeros((nCobras, maxTagetsPerCobra))
    counter = 0
    
    for i in range(len(nTargetsPerCobra)):
        # Get the target indices and distances for this cobra
        nTargetsForThisCobra = nTargetsPerCobra[i]
        targetsForThisCobra = targets[counter:counter + nTargetsForThisCobra]
        distancesForThisCobra = distances[counter:counter + nTargetsForThisCobra]

        # Sort the targets by their distance to the cobra and fill the arrays
        orderedIndices = distancesForThisCobra.argsort()
        targetIndices[i, :nTargetsForThisCobra] = targetsForThisCobra[orderedIndices]
        targetDistances[i, :nTargetsForThisCobra] = distancesForThisCobra[orderedIndices]

        # Increase the counter
        counter += nTargetsForThisCobra

    return (targetIndices, targetDistances)


def assignTargetsByDistance(targetIndices, targetDistances):
    """Assigns a single target to each cobra based on the target distance.
    
    This method assumes that the input arrays are ordered by the target 
    distance to the center of the cobra.

    Parameters
    ----------
    targetIndices: object
        A numpy array with the indices of the targets that can be reached by
        a given cobra.
    targetDistances: object
        A numpy array with the distances of the targets that can be reached by
        a given cobra.
    
    Returns
    -------
    tuple
        A numpy array with the indices of the targets assigned to each cobra.

    """
    # Assign targets to cobras looping from the closest to the more far away
    # ones
    (nCobras, maxTargetsPerCobra) = targetIndices.shape
    assignedTargets = np.full(nCobras, NULL_TARGET_INDEX, dtype="int")       
    freeCobras = np.full(nCobras, True, dtype="bool")
    freeTargets = np.full(targetIndices.max() + 1, True, dtype="bool")

    for i in range(maxTargetsPerCobra):
        # Get a list with the unique targets in the given column
        columnTargetIndices = targetIndices[:, i]
        uniqueTargetIndices = np.unique(columnTargetIndices[freeCobras])

        # Remove from the list the NULL_TARGET_INDEX value if it's present 
        uniqueTargetIndices = uniqueTargetIndices[uniqueTargetIndices != NULL_TARGET_INDEX]
        
        # Select free targets only
        uniqueTargetIndices = uniqueTargetIndices[freeTargets[uniqueTargetIndices]]
        
        # Loop over the unique target indices
        for targetIndex in uniqueTargetIndices:    
            # Get the free cobras for which this target is the closest in the
            # current column
            (associatedCobras,) = np.where(np.logical_and(columnTargetIndices == targetIndex, freeCobras))
            
            # Check how many associated cobras we have
            if len(associatedCobras) == 1:
                # Use this single cobra for this target
                cobraToUse = associatedCobras[0]
            else:
                # Select the cobras for which this is the only target
                accessibleTargets = targetIndices[associatedCobras, i:]
                targetIsAvailable = np.logical_and(accessibleTargets != NULL_TARGET_INDEX, freeTargets[accessibleTargets])
                nAvailableTargets = np.sum(targetIsAvailable, axis=1)
                singleTargetCobras = associatedCobras[nAvailableTargets == 1]
                
                # Decide depending on how many of these cobras we have
                if len(singleTargetCobras) == 0:
                    # All cobras have multiple targets: select the closest
                    # cobra
                    distances = targetDistances[associatedCobras, i]
                    cobraToUse = associatedCobras[distances.argmin()]
                elif len(singleTargetCobras) == 1:
                    # Assign the target to the cobra that can only reach this
                    # target
                    cobraToUse = singleTargetCobras[0]
                else:
                    # Assign the target to the closest single target cobra
                    distances = targetDistances[singleTargetCobras, i]
                    cobraToUse = singleTargetCobras[distances.argmin()]

            
            # Assign the target to the selected cobra
            assignedTargets[cobraToUse] = targetIndex
            freeCobras[cobraToUse] = False
            freeTargets[targetIndex] = False

    return assignedTargets


def solveCobraCollisions(assignedTargets, targetIndices, targetPositions, bench):
    """Detects and solves cobra collisions assigning them alternative targets.

    This method assumes that the targetIndices array is ordered by the target
    distance to the center of the cobra.

    This method changes the assignedTargets input array.

    Parameters
    ----------
    assignedTargets: object
        A numpy array with the indices of the targets assigned to each cobra.
    targetIndices: object
        A numpy array with the indices of the targets that can be reached by
        a given cobra.
    targetPositions: object
        A complex numpy array with the targets coordinates.
    bench: object
        The bench geometry to use.
    
    Returns
    -------
    tuple
        A complex numpy array with the cobras fiber positions.

    """
    # Set the fiber positions to their associated target positions, leaving 
    # unused cobras at their home positions 
    fiberPositions = bench["home0"].copy()
    usedCobras = assignedTargets != NULL_TARGET_INDEX
    fiberPositions[usedCobras] = targetPositions[assignedTargets[usedCobras]]  

    # Get the indices of the cobras where we have a collision
    (problematicCobras, nearbyProblematicCobras) = getProblematicCobras(fiberPositions, bench)
 
    # Try to solve the collisions one by one
    freeTargets = np.full(len(targetPositions), True, dtype="bool")
    freeTargets[assignedTargets[usedCobras]] = False
    
    for c, nc in zip(problematicCobras, nearbyProblematicCobras):
        # We only need to solve the first half of the problematic cases
        if nc > c:
            # Check if one of the colliding cobras is unused
            if assignedTargets[c] == NULL_TARGET_INDEX or assignedTargets[nc] == NULL_TARGET_INDEX:
                # The unused cobra is the cobra that we are going to move
                cobraToMove = c if (assignedTargets[c] == NULL_TARGET_INDEX) else nc

                # Rotate the cobra until we find a position with zero collisions
                cobraCenter = bench["center"][cobraToMove]
                initialPosition = fiberPositions[cobraToMove]
                bestPosition = initialPosition
               
                for ang in np.linspace(0, 2 * np.pi, 7)[1:-1]:
                    # Rotate the cobra around its center
                    fiberPositions[cobraToMove] = (initialPosition - cobraCenter) * np.exp(1j * ang) + cobraCenter
                    
                    # Exit the loop if we found a fiber position with zero collisions
                    if getCollisionsForCobra(cobraToMove, fiberPositions, bench) == 0:
                        bestPosition = fiberPositions[cobraToMove]
                        break

                # Use the best fiber position
                fiberPositions[cobraToMove] = bestPosition
            else:
                # Calculate the initial number of collisions associated with the two cobras
                collisions = getCollisionsForCobra(c, fiberPositions, bench)
                collisions += getCollisionsForCobra(nc, fiberPositions, bench)

                # Free the current targets
                initialTarget1 = assignedTargets[c]
                initialTarget2 = assignedTargets[nc]
                freeTargets[initialTarget1] = True
                freeTargets[initialTarget2] = True

                # Get the targets that can be reached by each cobra
                targets1 = targetIndices[c][targetIndices[c] != NULL_TARGET_INDEX]
                targets2 = targetIndices[nc][targetIndices[nc] != NULL_TARGET_INDEX]
                
                # Select only the free targets
                targets1 = targets1[freeTargets[targets1]]
                targets2 = targets2[freeTargets[targets2]]
                
                # Create two arrays reflecting all the possible target combinations
                targetsCombination1 = np.repeat(targets1, len(targets2))
                targetsCombination2 = np.tile(targets2, len(targets1))
                
                # Exclude the current target combination and combinations that
                # use the same target for the two cobras
                validCombinations = np.logical_or(targetsCombination1 != initialTarget1, targetsCombination2 != initialTarget2)
                validCombinations = np.logical_and(validCombinations, targetsCombination1 != targetsCombination2)
                targetsCombination1 = targetsCombination1[validCombinations]
                targetsCombination2 = targetsCombination2[validCombinations]
                
                # Loop over all the possible combinations until we find the minimum 
                # number of collisions
                bestTarget1 = initialTarget1    
                bestTarget2 = initialTarget2    

                for newTarget1, newTarget2 in zip(targetsCombination1, targetsCombination2):
                    # Assign the new fiber positions
                    fiberPositions[c] = targetPositions[newTarget1]
                    fiberPositions[nc] = targetPositions[newTarget2]
                    
                    # Calculate the number of collisions at the current positions 
                    currentCollisions = getCollisionsForCobra(c, fiberPositions, bench)
                    currentCollisions += getCollisionsForCobra(nc, fiberPositions, bench)
                               
                    # Check if the number of collisions decreased significantly.
                    # A decrease of one means that we solved the current collision,
                    # but we created a new collision with another nearby cobra.
                    if currentCollisions <= collisions - 2:
                        # Save the information from these targets
                        bestTarget1 = newTarget1
                        bestTarget2 = newTarget2
                        collisions = currentCollisions
                    
                    # Exit the loop if the number of collisions is already zero
                    if collisions == 0:
                        break
                
                # Use the targets where we had less collisions
                assignedTargets[c] = bestTarget1
                assignedTargets[nc] = bestTarget2
                fiberPositions[c] = targetPositions[bestTarget1]
                fiberPositions[nc] = targetPositions[bestTarget2]
                freeTargets[bestTarget1] = False
                freeTargets[bestTarget2] = False
    
    return fiberPositions


def getCollisionsForCobra(cobraIndex, fiberPositions, bench):
    """Calculates the number of collisions of a given cobra with its neighbors.
    
    Parameters
    ----------
    cobraIndex: int
        The index of the cobra for which we want to count the cobra collisions.
    fiberPositions: object
        A complex numpy array with the cobras fiber positions.
    bench: object
        The bench geometry to use.

    Returns
    -------
    int
        The number of collisions between this cobra and its neighbors.
    
    """  
    # Get the cobra neighbors from the bench precalculated information
    nearbyCobras = bench["NN"]["col"][bench["NN"]["row"] == cobraIndex]

    # Calculate the cobras rotation angles to reach the given positions
    allIndices = np.append(cobraIndex, nearbyCobras)
    cobraCenters = bench["center"][allIndices]
    L1 = bench["L1"][allIndices]
    L2 = bench["L2"][allIndices]
    (tht, phi) = benchUtils.getCobraRotationAngles(fiberPositions[allIndices] - cobraCenters, L1, L2)

    # Compute the cobras elbow positions
    cobraElbows = cobraCenters + L1 * np.exp(1j * tht)

    # Calculate the distances between the cobra link and the nearby cobras links
    startPoints1 = np.repeat(fiberPositions[cobraIndex], len(nearbyCobras))
    endPoints1 = np.repeat(cobraElbows[0], len(nearbyCobras))
    startPoints2 = fiberPositions[nearbyCobras]
    endPoints2 = cobraElbows[1:]
    distances = distanceBetweenLineSegments(startPoints1, endPoints1, startPoints2, endPoints2)

    # Get the cobra collisions for the current configuration
    cobraCollisions = distances < (bench["minDist"][cobraIndex] + bench["minDist"][nearbyCobras]) / 2

    return np.sum(cobraCollisions)


def getProblematicCobras(fiberPositions, bench):
    """Obtains the indices of the cobras involved in collisions.
    
    Parameters
    ----------
    fiberPositions: object
        A complex numpy array with the cobras fiber positions.
    bench: object
        The bench geometry to use.

    Returns
    -------
    tuple
        A python tuple with the indices of the cobras involved in collisions
        and the indices of the nearby cobras with which they collide.
    
    """
    # Calculate the cobras rotation angles to reach the given positions
    cobraCenters = bench["center"]
    L1 = bench["L1"]
    L2 = bench["L2"]
    (tht, phi) = benchUtils.getCobraRotationAngles(fiberPositions - cobraCenters, L1, L2)
    
    # Compute the cobras elbow positions
    cobraElbows = cobraCenters + L1 * np.exp(1j * tht)
  
    # Get the bench precalculated nearest neighbors information
    cobras = bench["NN"]["row"]
    nearbyCobras = bench["NN"]["col"]
    
    # We only need to test half of the cobra associations
    uniqueAssociations = cobras < nearbyCobras
    cobras = cobras[uniqueAssociations]
    nearbyCobras = nearbyCobras[uniqueAssociations]
    
    # Calculate the distances between the cobras links and the nearby cobras links
    startPoints1 = fiberPositions[cobras]
    endPoints1 = cobraElbows[cobras]
    startPoints2 = fiberPositions[nearbyCobras]
    endPoints2 = cobraElbows[nearbyCobras]
    distances = distanceBetweenLineSegments(startPoints1, endPoints1, startPoints2, endPoints2)

    # Get the cobra collisions for the current configuration
    cobraCollisions = distances < (bench["minDist"][cobras] + bench["minDist"][nearbyCobras]) / 2

    # Obtain the indices of the problematic cobras and their associations and
    # don't forget to include the other half of the associations
    problematicCobras = np.concatenate((cobras[cobraCollisions], nearbyCobras[cobraCollisions]))
    nearbyProblematicCobras = np.concatenate((nearbyCobras[cobraCollisions], cobras[cobraCollisions]))

    return (problematicCobras, nearbyProblematicCobras)


def distanceBetweenLineSegments(startPoints1, endPoints1, startPoints2, endPoints2):
    """Calculates the minimum distances between line segments.
    
    Parameters
    ----------
    startPoints1: object
        A complex numpy array with the first line segment start coordinates.
    endPoints1: object
        A complex numpy array with the first line segment end coordinates. 
    startPoints2: object
        A complex numpy array with the second line segment start coordinates. 
    endPoints2: object
        A complex numpy array with the second line segment end coordinates. 

    Returns
    -------
    object
        A numpy array with the minimum distance between the line segments.
        
    """
    # Calculate the minimum distances for each point to segment combination
    distances1 = distanceToLineSegment(startPoints1, startPoints2, endPoints2)
    distances2 = distanceToLineSegment(endPoints1, startPoints2, endPoints2)
    distances3 = distanceToLineSegment(startPoints2, startPoints1, endPoints1)
    distances4 = distanceToLineSegment(endPoints2, startPoints1, endPoints1)

    # Return the minimum distances
    return np.min((distances1, distances2, distances3, distances4), axis=0)


def distanceToLineSegment(points, startPoints, endPoints):
    """Calculates the minimum distances between points and line segments.
    
    Parameters
    ----------
    points: object
        A complex numpy array with the point coordinates. 
    startPoints: object
        A complex numpy array with the line segments start coordinates. 
    endPoints: object
        A complex numpy array with the line segments end coordinates. 

    Returns
    -------
    object
        A numpy array with the minimum distances between the points and the 
        line segments.
        
    """
    # Translate the points and the line segment end points to the line segment
    # starting points
    translatedPoints = points - startPoints
    translatedEndPoints = endPoints - startPoints
    
    # Rotate the translated points to have the line segment on the x axis
    rotatedPoints = translatedPoints * np.exp(-1j * np.angle(translatedEndPoints))
    
    # Define 3 regions for the points: left of the origin, over the line 
    # segments, and right of the line segments
    x = rotatedPoints.real
    lineLengths = np.abs(translatedEndPoints)
    (region1,) = np.where(x <= 0)
    (region2,) = np.where(np.logical_and(x > 0 , x < lineLengths))
    (region3,) = np.where(x >= lineLengths)

    # Calculate the minimum distances in each region
    distances = np.empty(len(points))
    distances[region1] = np.abs(rotatedPoints[region1])
    distances[region2] = np.abs(rotatedPoints[region2].imag)
    distances[region3] = np.abs(rotatedPoints[region3] - lineLengths[region3])

    return distances


def plotTargets(targetPositions, targetColors="0.4"):
    """Plots a list of targets.

    Parameters
    ----------
    targetPositions: object
        A complex numpy array with the targets coordinates.
    targetColors: object, optional
        The target colors. Default is grey.
    
    """
    plotUtils.addPoints(targetPositions, s=2, facecolor=targetColors)


if __name__ == "__main__":
    # Import the necessary modules
    import time as time
    import ics.cobraOps.cobraUtils as cobraUtils

    # Define the target density to use
    targetDensity = 2
    
    # Get the cobras central positions for the full PFI
    start = time.time()
    cobraCenters = cobraUtils.getCobrasCenters("full")
    print("Number of cobras:", len(cobraCenters))

    # Define the bench geometry
    bench = benchUtils.defineBenchGeometry(cobraCenters, True, True)

    # Create a random sample of targets
    targetPositions = generateTargets(targetDensity, bench)
    print("Number of simulated targets:", len(targetPositions))

    # Assign the target to the cobras and get the fiber positions
    (assignedTargets, fiberPositions) = assignTargets(targetPositions, bench)
    
    # Get the cobras for which the collision could not solved
    (problematicCobras, nearbyProblematicCobras) = getProblematicCobras(fiberPositions, bench)
    print("Number of unsolved collisions:", len(problematicCobras) / 2)
    print("Total computation time (s):", time.time() - start)

    # Plot the cobra-target associations
    start = time.time()    
    plotUtils.createNewFigure("Cobra-target associations", "x position", "y position")

    patrolAreaColors = np.full((len(cobraCenters), 4), [0.0, 0.0, 1.0, 0.15])
    patrolAreaColors[problematicCobras] = [0.0, 1.0, 0.0, 0.5]
    benchUtils.plotBenchGeometry(bench, patrolAreaColors)
    
    cobraColors = np.full((len(cobraCenters), 4), [0.0, 0.0, 1.0, 0.5])
    cobraColors[assignedTargets == NULL_TARGET_INDEX] = [1.0, 0.0, 0.0, 0.25]
    benchUtils.plotCobras(bench, fiberPositions, cobraColors)
    
    targetColors = np.full((len(targetPositions), 4), [0.4, 0.4, 0.4, 1.0])
    targetColors[assignedTargets[assignedTargets != NULL_TARGET_INDEX]] = [1.0, 0.0, 0.0, 1.0]
    plotTargets(targetPositions, targetColors)

    print("Plotting time (s):", time.time() - start)
    plotUtils.pauseExecution()
