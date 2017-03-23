import cv2
import numpy as np
import VisionUtils
import Utils
from collections import namedtuple
from time import time


class Line:
    def __init__(self, p1, p2):
        # Point: [x, y] or (x, y)
        self.p1 = tuple(p1)
        self.p2 = tuple(p2)

        self.angle = Utils.lineAngle(self.p1, self.p2)
        if self.angle < 0: self.angle += 180

    def __str__(self):
        return "Angle: " + str(self.angle) + "  P1: " + str(self.p1) + "  P2: " + str(self.p2)

class Mapper:
    """
    This class keeps track of new lines and identifies if the newly recognized line is consistent with the last
    few frames or if it's a mistake from bad line.

    It also performs the important task of keeping track of the map, where junctions are, and attempting to localize
    the robot within what it knows of the lines so far.
    """

    def __init__(self, p1, p2):
        self.history = []  # A list of line lists [[L1, L2], [L1, L2, L3] from previous frames
        self.currentLine = None

    def addLineFrame(self, lines):
        """
        :param lines: A list of [Line, Line] that the camera thinks it has found
        :return:
        """

        if len(lines) == 0: return

        if len(self.history) == 0:
            self.history.append(lines)

        self.currentLine = self.history[-1][0]

    def getCurrentLine(self):
        return self.currentLine.angle



class FollowLine:

    def __init__(self, parent):
        self.rover = parent
        self.map   = Mapper()

    def update(self):
        lowRed  = [150, 75, 75]
        highRed = [30, 255, 255]

        lines = self.__findLines(lowRed, highRed)
        self.map.addLineFrame(lines)

        line = self.map.getCurrentLine()  # Gets direction of the currently followed line
        print(line)


    def __findLines(self, hueLow, hueHigh):
        img   = self.rover.camera.read()

        rImg  = VisionUtils.isolateColor(img,   hueLow,  hueHigh)
        rGray = cv2.cvtColor(rImg, cv2.COLOR_BGR2GRAY)
        ret, rThresh = cv2.threshold(rGray, 50, 255, cv2.THRESH_BINARY)

        # Make the image small to reduce line-finding processing times
        small = cv2.resize(rThresh, (64, 48), interpolation=cv2.INTER_AREA)

        # cv2.imshow('Thresh', rThresh)


        # lines = cv2.HoughLinesP(edges, 1, np.pi, threshold=25, minLineLength=50, maxLineGap=10)
        lines = cv2.HoughLinesP(small, 1, np.pi/200, threshold=25, minLineLength=20, maxLineGap=10)


        if lines is None: return []

        # If lines were found, combine them until you have 1 average for each 'direction' of tape in the photo
        lines = [line[0] for line in lines]
        combinedLines = self.__combineLines(lines)


        return combinedLines

    def __combineLines(self, unsortedLines):
        """ Combines similar lines into one large 'average' line """
        print("len", len(unsortedLines))
        maxAngle = 45
        minLinesForCombo = 5

        def getAngle(line):
            # Turn angle from -180:180 to just 0:180
            angle = Utils.lineAngle(line[:2], line[2:])
            if angle < 0: angle += 180
            return angle

        def lineFits(checkLine, combo):
            """ Check if the line fits within this group of combos by checking it's angle """
            checkAngle = getAngle(checkLine)
            for line in combo:
                angle = Utils.lineAngle(line[:2], line[2:])
                difference = abs(checkAngle - angle)

                if difference < maxAngle or 180 - difference < maxAngle:
                    return True
                # if difference > maxAngle * 2 or 180 - difference > maxAngle * 2:
                #     return False
            return False

        # Pre-process lines so that lines always point from 0 degrees to 180, and not over
        for i, line in enumerate(unsortedLines):
            angle = Utils.lineAngle(line[:2], line[2:])
            if angle < 0:
                line = np.concatenate((line[2:], line[:2]))
                unsortedLines[i] = line


        # Get Line Combos
        lineCombos = []  # Format: [[[l1, l2, l3], [l4, l5, l6]], [[line 1...], [line 2...]]]

        while len(unsortedLines) > 0:
            checkLine = unsortedLines.pop(0)

            isSorted = False
            for i, combo in enumerate(lineCombos):
                if lineFits(checkLine, combo):
                    # Process the line so that the [x1, y1, and x2, y2] are in the same positions as other combos
                    lineCombos[i].append(checkLine.tolist())
                    isSorted = True
                    break

            if not isSorted:
                lineCombos.append([checkLine.tolist()])


        # # Limit each combo to minSamples, keeping only the longest lines
        # lineCombos = [sorted(combo, key= lambda c: (c[0] - c[2]) ** 2 + (c[1] - c[3]) ** 2, reverse=True)
        #               for combo in lineCombos]
        # lineCombos = [combo[:minLinesForCombo] for combo in lineCombos]


        # Filter and Average Combo Groups Format: [[L1], [L2], [L3]]
        averagedCombos = []
        for combo in lineCombos:
            if len(combo) < minLinesForCombo: continue

            avgLine = (np.sum(combo, axis=0) / len(combo)).astype(int)
            averagedCombos.append(Line(avgLine[:2], avgLine[2:]))

        return averagedCombos

        # Draw Line Combos and Final Lines
        # img = self.rover.camera.read()
        # for i, combo in enumerate(lineCombos):
        #     for x1, y1, x2, y2 in combo:
        #         x1 *= 10
        #         y1 *= 10
        #         x2 *= 10
        #         y2 *= 10
        #
        #         cv2.line(img, (x1, y1), (x2, y2), (80*i, 80*i, 80*i), 2)
        # if len(averagedCombos):
        #     for x1, y1, x2, y2 in averagedCombos:
        #         x1 *= 10
        #         y1 *= 10
        #         x2 *= 10
        #         y2 *= 10
        #
        #         cv2.line(img, (x1, y1), (x2, y2), (80, 80, 80), 8)
        #
        # cv2.imshow('final', img)
        # cv2.waitKey(2500)





