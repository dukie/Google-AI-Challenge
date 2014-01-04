#!/usr/bin/env python3.3
from abc import abstractmethod
from random import shuffle
import time
from ants import *
import sys

# Swarm composition constants
DEF_PLUS_SCOUTS_CRITICAL = 20
SCOUT_CRITICAL = 15

#Timeout constants
FINALIZE_TIME = 0.05
TURN_TIMEOUT = 20000.0


f = sys.stdout
turn_number = 0
bot_version = 'v0.1'


class MyAnt:
    #TODO Could be replaced by strategy pattern
    scouts = 0
    foodAnts = 0
    fighters = 0
    defAnts = 0
    antsObject = None

    @abstractmethod
    def __init__(self, pos):
        self.currentPosition = pos
        self.attack_hill = False
        self.is_working = False
        self.destination = None
        self.nextTurnPosition = pos
        self.myWay = []
        self.reorder = None
        self.target = None
        self.setupTarget()
        self.addAnt()

    @abstractmethod
    def died(self):
        pass

    @abstractmethod
    def addAnt(self):
        pass

    @abstractmethod
    def setupTarget(self):
        pass

    @abstractmethod
    def getTarget(self):
        return self.target

    @abstractmethod
    def update(self):
        pass


class ScoutAnt(MyAnt):
    def setupTarget(self):
        tmp = Swarm.getSwarmInformation().closest_food(self.currentPosition[0], self.currentPosition[1],
                                                       Swarm.getHunted())
        if tmp:
            self.target = tmp
            return True
            #very rich CPU function!!! need alternative
        self.target = Swarm.getSwarmInformation().closest_unseen(self.currentPosition[0], self.currentPosition[1],
                                                                 Swarm.getHunted())
        if self.target:
            return True
        else:
            return False

    def order(self):
        #dest = self.target
        if self.target in Swarm.getSwarmInformation().food() and self.target != Swarm.getHunted():
            return True
            #if self.target: return True
        return self.setupTarget()

    def update(self):
        pass

    def addAnt(self):
        MyAnt.scouts += 1

    def died(self):
        MyAnt.scouts -= 1


class FoodAnt(MyAnt):
    def setupTarget(self):
        if not Swarm.getDiscoveredHills():
            self.target = Swarm.getSwarmInformation().closest_enemy_ant(self.currentPosition[0],
                                                                        self.currentPosition[1], Swarm.getHunted())
            if self.target:
                return True
            else:
                self.target = Swarm.getSwarmHills()[0]
                return True
        else:
            self.target = Swarm.getDiscoveredHills()[0]
            return True

    def order(self):
        return self.setupTarget()

    def update(self):
        pass

    def addAnt(self):
        MyAnt.foodAnts += 1

    def died(self):
        MyAnt.foodAnts -= 1


class DefAnt(MyAnt):
    def setupTarget(self):
        self.target = Swarm.getSwarmInformation().closest_enemy_ant(self.currentPosition[0], self.currentPosition[1],
                                                                    Swarm.getHunted())
        if self.target:
            return True
        else:
            self.target = Swarm.getSwarmHills()[0]
            return True

    def order(self):
        return self.setupTarget()

    def update(self):
        pass

    def addAnt(self):
        MyAnt.defAnts += 1

    def died(self):
        MyAnt.defAnts -= 1


class Swarm:
    sharedInformation = None
    hunted = []
    discoveredHills = []
    myHills = []

    def __init__(self, antsInformation):
        self.antsList = []
        self.timeout = float(antsInformation.turntime) / 1000 - FINALIZE_TIME
        self.turnStarted = None
        Swarm.sharedInformation = antsInformation

    def prepareForNextTurn(self):
        self.turnStarted = time.time()

        Swarm.myHills = set([hill for hill in Swarm.getSwarmInformation().my_hills()])
        self.scoutsNum = len(Swarm.getSwarmInformation().map) * len(Swarm.getSwarmInformation().map[0]) // 512
        oldAntsPositionsList = []
        newAntsPositionsList = set([ant for ant in Swarm.getSwarmInformation().my_ants()])
        temporaryAntsList = []

        for ant in self.antsList:
            if ant.nextTurnPosition in newAntsPositionsList:
                ant.currentPosition = ant.nextTurnPosition
                oldAntsPositionsList.append(ant.currentPosition)
                temporaryAntsList.append(ant)
            else:
                ant.died()

        self.antsList = temporaryAntsList
        newAnts = set(newAntsPositionsList) - set(oldAntsPositionsList)
        for newAnt in newAnts:
            if MyAnt.scouts < SCOUT_CRITICAL:
                self.antsList.append(ScoutAnt(newAnt))
            else:
                if MyAnt.scouts + MyAnt.defAnts > DEF_PLUS_SCOUTS_CRITICAL:
                    self.antsList.append(FoodAnt(newAnt))
                else:
                    if MyAnt.scouts < SCOUT_CRITICAL:
                        self.antsList.append(ScoutAnt(newAnt))
                    else:
                        self.antsList.append(DefAnt(newAnt))

        #logic for enemy hills trace
        eh = []
        for hill in self.discoveredHills:
            aRow, aCol = hill
            if HILL == Swarm.getSwarmInformation().map[aRow][aCol] or LAND == Swarm.getSwarmInformation().map[aRow][
                aCol]:
                eh.append(hill)
        Swarm.discoveredHills = eh
        eh = [hill for (hill, owner) in Swarm.getSwarmInformation().enemy_hills()]
        Swarm.discoveredHills = list(set(Swarm.discoveredHills) or set(eh))

    def getAnts(self):
        return self.antsList

    def update(self):

        destinations = []

        for ant in self.getAnts():
            timeDelta = time.time() - self.turnStarted
            #print("MSMS:", self.timeout)
            if timeDelta < self.timeout:

                if not ant.getTarget():
                    ant.myWay = []
                    ant.myWay.append(ant.currentPosition)
                    if ant.setupTarget():
                        self.calculateWay(ant, destinations)
                    else:
                        destinations.append(ant.currentPosition)
                else:
                    ant.order()
                    self.calculateWay(ant, destinations)
            else:
                break
        Swarm.hunted = []

    def calculateWay(self, ant, destinations):
        aRow, aCol = ant.currentPosition
        destination = ant.target
        directions = AIM.keys()
        shuffle(directions)
        result = maxint
        chosenDirection = None

        #TODO Implement obstacle detection algorithm

        for direction in directions:
            (nRow, nCol) = Swarm.getSwarmInformation().destination(aRow, aCol, direction)

            if not (nRow, nCol) in destinations and Swarm.getSwarmInformation().unoccupied(nRow,
                    nCol) and Swarm.getSwarmInformation().passable(nRow, nCol) and not (nRow, nCol) in ant.myWay:

                tempDistance = Swarm.getSwarmInformation().distance(nRow, nCol, destination[0], destination[1])
                if tempDistance <= result:
                    result = tempDistance
                    chosenDirection = direction

        if chosenDirection:
            return self.do_order(LAND, (aRow, aCol),
                                 Swarm.getSwarmInformation().destination(aRow, aCol, chosenDirection),
                                 destinations, ant, chosenDirection)

        ant.target = None
        return False

    def do_order(self, order_type, loc, destination, destinations, ant, direction):
        a_row, a_col = loc
        Swarm.getSwarmInformation().issue_order((a_row, a_col, direction))
        ant.myWay.append(destination)
        ant.nextTurnPosition = destination
        destinations.append(destination)
        Swarm.hunted.append(ant.target)
        return True

    @staticmethod
    def getSwarmInformation():
        return Swarm.sharedInformation

    @staticmethod
    def getHunted():
        return Swarm.hunted

    @staticmethod
    def getDiscoveredHills():
        return Swarm.discoveredHills

    @staticmethod
    def getSwarmHills():
        return Swarm.discoveredHills


class MyBot:
    def __init__(self):
        self.swarm = None

    def do_turn(self, newAntsInformation):
        if not self.swarm:
            self.swarm = Swarm(newAntsInformation)
        self.swarm.prepareForNextTurn()
        self.swarm.update()


if __name__ == '__main__':
    try:
        import psyco

        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
