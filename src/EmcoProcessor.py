# Required imports
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QGraphicsView, QMainWindow, QGraphicsScene, QTextBrowser, QScrollArea, QLineEdit, QLabel, QHBoxLayout, QGridLayout, QCheckBox, QTextEdit, QMessageBox, QGraphicsPathItem
from PyQt5.QtGui import QPen, QColor, QPainterPath
from PyQt5.QtCore import Qt, QRectF
import ezdxf
import os
import qdarktheme
import numpy as np
import decimal
import math

# Parses input file to extract entities relative to gcode
def parse_dxf_file(file_path):
    # Set the precision (number of decimal places)
    decimal.getcontext().prec = 2  # Change this to your desired precision

    # Set the rounding mode (optional, default is ROUND_HALF_EVEN)
    decimal.getcontext().rounding = decimal.ROUND_HALF_UP
    
    parsed_data = []
    doc = ezdxf.readfile(file_path)
    for entity in doc.modelspace():
        if entity.dxftype() == 'LINE':
            start_point = entity.dxf.start
            end_point = entity.dxf.end
            parsed_data.append({
                'type': 'LINE',
                'start_point': (round(start_point.x,2), round(start_point.y,2)),
                'end_point': (round(end_point.x,2), round(end_point.y,2))
            })
        elif entity.dxftype() == 'ARC':
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = entity.dxf.start_angle
            end_angle = entity.dxf.end_angle
            
            # Calculate the start and end points
            start_angle_rad = math.radians(start_angle)
            end_angle_rad = math.radians(end_angle)
            start_x = center.x + radius * math.cos(start_angle_rad)
            start_y = center.y + radius * math.sin(start_angle_rad)

            end_x = center.x + radius * math.cos(end_angle_rad)
            end_y = center.y + radius * math.sin(end_angle_rad)
            
            # Calculate arc direction for g02 g03
            # Calculate the angular difference between the start and end angles
            angle_difference = end_angle - start_angle
            direction = ""

            # Determine the direction based on the angle difference
            if angle_difference > 0:
                direction =  "cw"  # Positive angle difference indicates counterclockwise
            else:
                direction =  "ccw"  # Negative angle difference indicates clockwise
    
            
            # Ensure start and end points are in order
            start_point = (round(start_x,2), round(start_y,2))
            end_point = (round(end_x,2), round(end_y,2))
            if round(start_x,2) < round(end_x,2):
                temp = start_point
                start_point = end_point
                end_point = temp
                if direction == "cw":
                    direction = "ccw"
                else:
                    direction = "cw"
                
            parsed_data.append({
                    'type': 'ARC',
                    'center_point': (round(center.x,2), round(center.y,2)),
                    'radius': round(radius,2),
                    'start_angle': round(start_angle,2),
                    'end_angle': round(end_angle,2),
                    'start_point': start_point,
                    'end_point': end_point,
                    'direction': direction
                })
        elif entity.dxftype() == 'LWPOLYLINE':
            polyline_data = []
            for vertex in entity.points():
                polyline_data.append((round(vertex.x,2)), round(vertex.y,2))
            parsed_data.append({
                'type': 'POLYLINE',
                'vertices': polyline_data
            })

    return parsed_data

# block num space padding logic
def blockNumPad(blockNum, GcodeTrue):
    blockNumStr = ""
    if blockNum < 10:
        blockNumStr = "    0" + str(blockNum)
    elif blockNum < 100:
        blockNumStr = "    " + str(blockNum)
    else:
        blockNumStr = "   " + str(blockNum)
        
    if GcodeTrue:
        blockNumStr = blockNumStr + " "
    return blockNumStr

# Adjusts x coordinate based on stock radius, Lathe Z axis in implementation
def compX(xcoordinate, stockRadius):
    return xcoordinate - stockRadius

# returns a formated G01 command
def formatG00G01G02G03(xcord, ycord, gcodeType):
    # Set the precision (number of decimal places)
    decimal.getcontext().prec = 2  # Change this to your desired precision

    # Set the rounding mode (optional, default is ROUND_HALF_EVEN)
    decimal.getcontext().rounding = decimal.ROUND_HALF_UP
    
    # Both coordinates are negative
    if xcord < 0 and ycord < 0:
        return f'{gcodeType[1:]} -{abs(int(xcord*100)):04} -{abs(int(ycord*100)):05}'
    # Only X neg
    elif xcord < 0 and ycord >= 0:
        return f'{gcodeType[1:]} -{abs(int(xcord*100)):04}  {abs(int(ycord*100)):05}'
    # Only y neg    
    elif xcord >= 0 and ycord < 0:
        return f'{gcodeType[1:]}  {abs(int(xcord*100)):04} -{abs(int(ycord*100)):05}'
    # Both positive
    elif xcord >= 0 and ycord >=0:
        return f'{gcodeType[1:]}  {abs(int(xcord*100)):04}  {abs(int(ycord*100)):05}'

        
# Formats feedrate for gcode output
def formatFeed(feedrate):
    return f' {feedrate:03}'
    
# Sorts data being parsed from DXF so lines are in consecutive order
# Lines are in order starting from Z0 which should be where the 
#   start of the cut occurs
def sortParsedData(parsed_data):
    # Create a dictionary to map each endpoint to its corresponding line
    endpoint_to_line = {(line['start_point'][0], line['start_point'][1]): line for line in parsed_data}

    # Find the starting point (0)
    first_line = None
    for line in parsed_data:
        if line['start_point'][0] == 0:
            first_line = line
            break

    # Initialize the sorted list with the first line
    sorted_lines = [first_line]
    endpoint = first_line['end_point']

    # Continue to find and add consecutive lines
    while True:
        next_line = endpoint_to_line.get(endpoint)
        if next_line is None:
            break
        sorted_lines.append(next_line)
        endpoint = next_line['end_point']
        
    return sorted_lines

# FLips a DXF file over the x azis (machine z) so that you can draw in the 
#   positive or negative y axis
def flipDXFOverX(parsed_data):
    if parsed_data[0]['start_point'][1] < 0 :
        for item in parsed_data:
            # flip start point y
            if 'start_point' in item:
                item['start_point'] = (item['start_point'][0], abs(item['start_point'][1]))

            # flip end point y 
            if 'end_point' in item:
                item['end_point'] = (item['end_point'][0], abs(item['end_point'][1]))

            # flip center point if arc
            if 'center_point' in item:
                item['center_point'] = (item['center_point'][0],abs(item['center_point'][1]))
                
#             # change start angle if arc
#             if 'start_angle' in item:
#                 # do nothing?
                
#             # change end angle if arc
#             if 'end_angle' in item:
#                 # do nothing?
                
            # change direction if arc
            if 'direction' in item:
                if item['direction'] == "cw":
                    item['direction'] = "ccw"
                else:
                    item['direction'] = "cw"
                    
    return parsed_data

# Adds final blocks to gcode. Included M30, M5
def addFinishingBlocks(gcode, blockNum, isUseM3M5Checked):
    # ending blocks
    if isUseM3M5Checked:
        gcode.append(f'{blockNumPad(blockNum, 0)}M05\n')
        blockNum +=1

    # File end
    gcode.append(f'{blockNumPad(blockNum, 0)}M30\n')
    blockNum += 1
    return gcode, blockNum

# Adds starting bocks. Includes retract, M3
def addStartingBlocks(gcode, blockNum, isUseM3M5Checked, isStartRetractXChecked, isStartRetractZChecked, isStartRetractXZChecked):
    # Check if using m3/m5
    def usingM3M5(blockNum):
        if isUseM3M5Checked:
            gcode.append(f'{blockNumPad(blockNum, 0)}M03\n')
            blockNum +=1
        return blockNum
    
    # Check stating retracts
    if isStartRetractXChecked:
        # The "Retract before start in X" checkbox is checked
        gcode.append(f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(.50, 0, "G00")}\n')
        blockNum += 1
        blockNum = usingM3M5(blockNum)
        gcode.append(f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(-.50, 0, "G00")}\n')
        blockNum += 1
    elif isStartRetractZChecked:
        # The "Retract bblockNumefore start in Z" checkbox is checked
        gcode.append(f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(0, .50, "G00")}\n')
        blockNum += 1
        blockNum = usingM3M5(blockNum)
        gcode.append(f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(0, -.50, "G00")}\n')
        blockNum += 1
    elif isStartRetractXZChecked:
        # The "ReblockNumtract before start in X and Z" checkbox is checked
        gcode.append(f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(.50, .50, "G00")}\n')
        blockNum += 1
        blockNum = usingM3M5(blockNum)
        gcode.append(f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(-.50, -.50, "G00")}\n')
        blockNum += 1
    else:
        blockNum = usingM3M5(blockNum)
        
    return gcode, blockNum

# Returns the smallest y value of the parsed data. Machine X axis
def find_smallest_y(parsed_data):
    # Initialize with a large value to ensure any Y coordinate is smaller
    smallest_y = float('inf')

    for entity in parsed_data:
        if 'start_point' in entity:
            smallest_y = min(smallest_y, entity['start_point'][1])
        if 'end_point' in entity:
            smallest_y = min(smallest_y, entity['end_point'][1])
        # Add similar checks for other entity types, e.g., 'center_point' for arcs

    return smallest_y

# Adds final blocks to gcode. Included retract, M30, M5
def addRetract(gcode, blockNum, current_x, current_y):
    # final retract to beginning of cut
    toAppend = (f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(-current_x, 0, "G00")}\n')
    gcode.append(toAppend)
    blockNum += 1
    toAppend = (f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(0, -current_y, "G00")}\n')
    gcode.append(toAppend)
    blockNum += 1
    return gcode, blockNum

# Adds the block num to roughing subroutine calls
def addSubStartBlock(gcode, sub_start_num):
    modified_gcode_lines = []
    for line in gcode:
        if "25+blockNumRough" in line:
            # Replace "G25" with "G25 BlockNum"
            modified_line = line.replace("25+blockNumRough", f"25             L{sub_start_num:03}")
            modified_gcode_lines.append(modified_line)
        else:
            modified_gcode_lines.append(line)
    return modified_gcode_lines

# Creates toolpath gcode calls
def createToolpath(gcode, parsed_data, blockNum, current_x, current_y, stockRadius, roughFeed, finishFeed, isRoughing):
    # generate subroutine gcode blocks
    if isRoughing == 0:
        roughFeed = finishFeed
        
    for entity in parsed_data:
        toAppend = ""
        isArc = 0
        if entity['type'] == 'LINE':
            end_x, end_y = entity['end_point']
            gotoX = compX(end_y, stockRadius) - current_x
            current_x = compX(end_y, stockRadius)   
            gotoY = end_x - current_y
            current_y = end_x
            gcodeToAdd = (f'{formatG00G01G02G03(gotoX, gotoY, "G01")}{formatFeed(roughFeed)}')
        elif entity['type'] == 'ARC':
            center_x, center_y = entity['center_point']
            radius = entity['radius']
            start_angle = entity['start_angle']
            end_angle = entity['end_angle']
            start_x, start_y = entity['start_point']
            direction = entity['direction']

            if direction == "ccw":
                # First line with M03: Include end point relative to the center
                end_x, end_y = entity['end_point']
                gotoX = compX(end_y, stockRadius) - current_x
                current_x = compX(end_y, stockRadius)   
                gotoY = end_x - current_y
                current_y = end_x
                gcodeToAdd = (f'{formatG00G01G02G03(gotoX, gotoY, "G02")}{formatFeed(roughFeed)}\n')
            else:
                # First line with M02: Include end point relative to the center
                end_x, end_y = entity['end_point']
                gotoX = compX(end_y, stockRadius) - current_x
                current_x = compX(end_y, stockRadius)   
                gotoY = end_x - current_y
                current_y = end_x
                gcodeToAdd = (f'{formatG00G01G02G03(gotoX, gotoY, "G03")}{formatFeed(roughFeed)}\n')

            # Calculate the relative distance to the center
            relative_x = end_x - center_x
            relative_y = end_y - center_y

            # Second line with M99: Include relative distance to the center
            gcodeToAdd = (f'{gcodeToAdd}{blockNumPad(blockNum+1, 0)}M99 I{abs(int(relative_x*100)):04} K{abs(int(relative_y*100)):05}')
            isArc = 1
        elif entity['type'] == 'POLYLINE':
            vertices = entity['vertices']
            for vertex in vertices:
                end_x = vertex[0]
                end_y = vertex[1]
                gotoX = compX(end_y, stockRadius) - current_x
                current_x = compX(end_y, stockRadius)   
                gotoY = end_x - current_y
                current_y = end_x
                gcodeToAdd = (f'{formatG00G01G02G03(gotoX, gotoY, "G01")}{formatFeed(roughFeed)}')

        # append to output
        toAppend = blockNumPad(blockNum, 1) + gcodeToAdd + "\n"
        gcode.append(toAppend)
        if isArc:
            blockNum += 2
        else:
            blockNum += 1
            
    # Insert final M17 sub return
    if isRoughing:
        gcode.append(f'{blockNumPad(blockNum, 0)}M17\n')
        
    return gcode, blockNum
        
# Parses DXF data into Emco supported GCode
def generate_gcode_from_dxf(parsed_data, isUseM3M5Checked, isStartRetractXChecked,isStartRetractZChecked, isStartRetractXZChecked, stockRadius, roughFeed, roughStep, finishFeed, finishStep):
    
    # starting blocks
    gcode = []
    blockNum = 0
    gcode.append(f'%\n')
    gcode.append(f'    N` G`   X `    Z `  F`  H\n')
    feed = roughFeed
    if (finishFeed == ""):
        finishFeed == roughFeed
    
    # generate starting blocks
    gcode, blockNum = addStartingBlocks(gcode, blockNum, isUseM3M5Checked, isStartRetractXChecked, isStartRetractZChecked, isStartRetractXZChecked)

    # Calculate stepovers
    parsed_data = sortParsedData(parsed_data)
    parsed_data = flipDXFOverX(parsed_data)
    number_of_steps = 1
    finish_steps = 0
    
    # Calculate number of steps
    if roughStep != 0:
        smallest_z = find_smallest_y(parsed_data)
        number_of_steps = int((stockRadius - smallest_z)/roughStep)
        if finishStep != 0:
            if ((stockRadius - smallest_z) % roughStep) / finishStep > 1:
                number_of_steps += 1
        
    # Generate move and sub calls
    step_num = 1
    while step_num - 1 != number_of_steps:
        
        # Set x offset accordingly
        # Roughing
        feed = roughFeed
        startXOffset = 0
        if roughStep != 0:
            if (stockRadius-smallest_z)-((step_num-1)*roughStep) > roughStep:
                startXOffset = (stockRadius - smallest_z) - (step_num * roughStep) 
            else:
                # Finishing
                stockLeft = (stockRadius-smallest_z)-((step_num-1)*roughStep)
                if stockLeft > finishStep:
                    startXOffset = stockLeft - (stockLeft - finishStep)
        
        # Calculate starting cut position and move there from X offset
        # Move to cut
        firstEndPoint = (parsed_data[0]['start_point'][0], parsed_data[0]['start_point'][1])
        toAppend = (f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(compX(firstEndPoint[1], stockRadius) + startXOffset, firstEndPoint[0], "G01")}{formatFeed(feed)}\n')
        gcode.append(toAppend)
        blockNum += 1
        
        # Add subroutine call
        gcode.append(f'{blockNumPad(blockNum, 1)}25+blockNumRough\n')
        blockNum += 1
        
        # Add retract
        retract_x = compX(parsed_data[-1]['end_point'][1], stockRadius) + startXOffset
        retract_y = parsed_data[-1]['end_point'][0]
        gcode, blockNum = addRetract(gcode, blockNum, retract_x, retract_y)
            
        # Update num steps
        step_num += 1
        
    # Blank lines for readability
    gcode.append(f'{blockNumPad(blockNum, 1)}21\n')
    blockNum += 1
    gcode.append(f'{blockNumPad(blockNum, 1)}21\n')
    blockNum += 1
    
    # Calculate starting positions of cut relatively 
    firstEndPoint = (parsed_data[0]['start_point'][0], parsed_data[0]['start_point'][1])
    current_x = compX(firstEndPoint[1], stockRadius)
    current_y = firstEndPoint[0]
    
    ##############
    # add finish subroutine
    ##############
    if roughStep != 0:
        # Move to cut
        firstEndPoint = (parsed_data[0]['start_point'][0], parsed_data[0]['start_point'][1])
        toAppend = (f'{blockNumPad(blockNum, 1)}{formatG00G01G02G03(compX(firstEndPoint[1], stockRadius), firstEndPoint[0], "G01")}{formatFeed(finishFeed)}\n')
        gcode.append(toAppend)
        blockNum += 1

        # Add finish pass
        gcode, blockNum = createToolpath(gcode, parsed_data, blockNum, current_x, current_y, stockRadius, roughFeed, finishFeed, 0)

        # Add retract
        retract_x = compX(parsed_data[-1]['end_point'][1], stockRadius)
        retract_y = parsed_data[-1]['end_point'][0]
        gcode, blockNum = addRetract(gcode, blockNum, retract_x, retract_y)
    
    ##############
    # end finish subroutine
    ##############
    
    # generate finishing blocks
    gcode, blockNum = addFinishingBlocks(gcode, blockNum, isUseM3M5Checked)
    gcode.append(f'{blockNumPad(blockNum, 1)}21\n')
    blockNum += 1
    gcode.append(f'{blockNumPad(blockNum, 1)}21\n')
    blockNum += 1
    
    # insert sub block number into sub calls
    gcode = addSubStartBlock(gcode, blockNum)
    
    # generate subroutine gcode blocks
    gcode, blockNum = createToolpath(gcode, parsed_data, blockNum, current_x, current_y, stockRadius, roughFeed, finishFeed, 1)

    # MFI end input
    gcode.append(f'   M\n')
    
    return gcode

# Determins the max DXF size for scaling DXF preview 
def calculate_drawing_extents(entities):
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    for entity in entities:
        if entity['type'] == 'LINE':
            start_x, start_y = entity['start_point']
            end_x, end_y = entity['end_point']
            min_x = min(min_x, start_x, end_x)
            max_x = max(max_x, start_x, end_x)
            min_y = min(min_y, start_y, end_y)
            max_y = max(max_y, start_y, end_y)
        elif entity['type'] == 'CIRCLE':
            center_x, center_y = entity['center_point']
            radius = entity['radius']
            min_x = min(min_x, center_x - radius)
            max_x = max(max_x, center_x + radius)
            min_y = min(min_y, center_y - radius)
            max_y = max(max_y, center_y + radius)
        elif entity['type'] == 'ARC':
            center_x, center_y = entity['center_point']
            radius = entity['radius']
            start_angle = entity['start_angle']
            end_angle = entity['end_angle']
            min_x = min(min_x, center_x - radius)
            max_x = max(max_x, center_x + radius)
            min_y = min(min_y, center_y - radius)
            max_y = max(max_y, center_y + radius)
        elif entity['type'] == 'POLYLINE':
            for vertex in entity['vertices']:
                x, y = vertex
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

    return min_x, min_y, max_x, max_y

# Emco Processor GUI
class DXFParserGUI(QWidget):
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.file_path = ""
        self.output_code = ""

    def initUI(self):
        layout = QVBoxLayout()

        # Display the DXF drawing
        self.view = QGraphicsView(self)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

        # Open DXF file button
        self.btn_open = QPushButton("Open DXF File")
        self.btn_open.clicked.connect(self.openFile)
        layout.addWidget(self.btn_open)

        # Create a grid layout for labels and text boxes
        grid_layout = QGridLayout()
        
        # Add a note for stepdowns
        self.stepdown_desc_label = QLabel("A roughing stepdown of 0 will cut the part in one go. A finishing stepdown of 0 will cut whatever is left after roughing in one go.")
        grid_layout.addWidget(self.stepdown_desc_label, 0, 1, 1, 10)

        # Stock Radius input
        self.stock_radius_label = QLabel("Stock Radius (mm):")
        self.stock_radius_input = QLineEdit()
        grid_layout.addWidget(self.stock_radius_label, 1, 0)
        grid_layout.addWidget(self.stock_radius_input, 1, 1)

        # Roughing Feedrate input
        self.roughing_feedrate_label = QLabel("Rough Feedrate (mm/min):")
        self.roughing_feedrate_input = QLineEdit()
        grid_layout.addWidget(self.roughing_feedrate_label, 1, 3)
        grid_layout.addWidget(self.roughing_feedrate_input, 1, 4)

        # Roughing Stepdown input
        self.roughing_stepdown_label = QLabel("Rough Stepdown (mm):")
        self.roughing_stepdown_input = QLineEdit()
        grid_layout.addWidget(self.roughing_stepdown_label, 1, 5)
        grid_layout.addWidget(self.roughing_stepdown_input, 1, 6)

        # Finishing Feedrate input
        self.finishing_feedrate_label = QLabel("Finish Feedrate (mm/min):")
        self.finishing_feedrate_input = QLineEdit()
        grid_layout.addWidget(self.finishing_feedrate_label, 1, 7)
        grid_layout.addWidget(self.finishing_feedrate_input, 1, 8)

        # Finishing Stepdown input
        self.finishing_stepdown_label = QLabel("Finish Stepdown (mm):")
        self.finishing_stepdown_input = QLineEdit()
        grid_layout.addWidget(self.finishing_stepdown_label, 1, 9)
        grid_layout.addWidget(self.finishing_stepdown_input, 1, 10)
        
        # add layout 1
        layout.addLayout(grid_layout)
        
        # Create a grid layout for check boxes
        grid_layout2 = QGridLayout()
        grid_layout2.setSpacing(150)
    
        # Use M3/M5 toggle button
        self.use_m3_m5_checkbox = QCheckBox("Use M3/M5")
        grid_layout2.addWidget(self.use_m3_m5_checkbox, 1, 0, 1, 1)
        
        # Retract in X, Z, or XZ toggle button 
        self.retract_start_x_checkbox = QCheckBox("Retract before start in X")
        grid_layout2.addWidget(self.retract_start_x_checkbox, 1, 2, 1, 3)
        self.retract_start_z_checkbox = QCheckBox("Retract before start in Z")
        grid_layout2.addWidget(self.retract_start_z_checkbox, 1, 4, 1, 5)
        self.retract_start_xz_checkbox = QCheckBox("Retract before start in X and Z")
        grid_layout2.addWidget(self.retract_start_xz_checkbox, 1, 6, 1, 7)

        
        # Create a list of the checkboxes for easier management
        retract_checkboxes = [
            self.retract_start_x_checkbox,
            self.retract_start_z_checkbox,
            self.retract_start_xz_checkbox
        ]
        
        # Connect the checkboxes to the mutually exclusive function
        for checkbox in retract_checkboxes:
            checkbox.clicked.connect(lambda state, c=checkbox: self.exclusive_retract_behavior(c, retract_checkboxes))
    
        # Add the grid layout to the main layout
        layout.addLayout(grid_layout2)

        # Scrollable G-code display that allows user to edit directly
        self.gcode_browser = QTextEdit(self)
        self.gcode_browser_cursor = self.gcode_browser.textCursor()
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.gcode_browser)
        layout.addWidget(self.scroll_area)
        self.scroll_area.setWidgetResizable(True)
        
        # Set the font size for the QTextBrowser
        font = self.gcode_browser.currentFont()
        font.setPointSize(14)  # Adjust the font size (in points) as needed
        self.gcode_browser.setFont(font)
        
        # Create a grid layout for generate and save buttons
        grid_layout3 = QGridLayout()
        
        # Add M00 button
        self.btn_M00 = QPushButton("Add M00")
        self.btn_M00.clicked.connect(self.insertM00)
        grid_layout3.addWidget(self.btn_M00, 0, 0)
        
        # Add M00 button
        self.btn_G21 = QPushButton("Add G21")
        self.btn_G21.clicked.connect(self.insertG21)
        grid_layout3.addWidget(self.btn_G21, 0, 1)
        
        # Finishing Stepdown input
        self.addM00_label = QLabel("Add at block number:")
        self.addM00G21_input = QLineEdit()
        self.addM00G21_input.setMaximumWidth(200)
        grid_layout3.addWidget(self.addM00_label, 0, 2)
        grid_layout3.addWidget(self.addM00G21_input, 1, 2)

        # Generate G-code button
        self.btn_gen = QPushButton("Generate G-code")
        self.btn_gen.clicked.connect(self.generateGCode)
        grid_layout3.addWidget(self.btn_gen, 0, 4)
        
        # Save G-code button
        self.btn_save = QPushButton("Save G-code")
        self.btn_save.clicked.connect(self.saveGCode)
        grid_layout3.addWidget(self.btn_save, 0, 5)
        
        # Add the grid layout to the main layout
        layout.addLayout(grid_layout3)

        self.setLayout(layout)
        self.setGeometry(100, 100, 1600, 1600)
        self.setWindowTitle("DXF Parser")
        self.show()
        
##############################################################################################
#################################  CALLBACK FUNCTIONS  #######################################
##############################################################################################

    # Function to read stock radius input
    def getStockRadius(self):
        if self.stock_radius_input.text() != "":
            return int(self.stock_radius_input.text())
        else:
            return ""
        
    # Function to read roughing feedrate
    def getRoughFeed(self):
        if self.roughing_feedrate_input.text() != "":
            return int(self.roughing_feedrate_input.text())
        else:
            return "" 
    
    # Function to read roughing feedrate
    def getFinishFeed(self):
        if self.finishing_feedrate_input.text() != "":
            return int(self.finishing_feedrate_input.text())
        else:
            return "" 
    
    # Function to read roughing feedrate
    def getRoughStep(self):
        if self.roughing_stepdown_input.text() != "":
            return int(self.roughing_stepdown_input.text())
        else:
            return "" 
        
    # Function to read finishing feedrate
    def getFinishStep(self):
        if self.finishing_stepdown_input.text() != "":
            return int(self.finishing_stepdown_input.text())
        else:
            return "" 
    
    # Function to get the value of the Use M3/M5 checkbox
    def isUseM3M5Checked(self):
        return self.use_m3_m5_checkbox.isChecked()
    
    # Functions to get the value of the start retract boxes
    def isStartRetractXChecked(self):
        return self.retract_start_x_checkbox.isChecked()
    
    def isStartRetractZChecked(self):
        return self.retract_start_z_checkbox.isChecked()
    
    def isStartRetractXZChecked(self):
        return self.retract_start_xz_checkbox.isChecked()
    
    # Insert M00 at cursor position in gcode output
    def insertM00(self):
        self.insertBlock("M00")
        
    # Insert 21 at cursor position in gcode output
    def insertG21(self):
        self.insertBlock("G21")
    
    # Insert M00, G21 at cursor position in gcode output
    def insertBlock(self, M00G21):
        
        # Insert M00 or popup error if block insertion number has been added
        currentBlock = self.addM00G21_input.text()
        if self.gcode_browser.toPlainText() == "":
            self.errorMessage("Please generate GCode first")
        elif currentBlock != "":
            currentBlock = int(currentBlock)
            text_to_insert = f"    {currentBlock:02d}  {M00G21}"  # Format the text
        
            # Get the entire text from the QTextEdit
            full_text = self.gcode_browser.toPlainText()

            # Split the text into lines
            lines = full_text.split('\n')

            # Update the block numbers in the lines
            updated_lines = []
            block_number = 0  # The starting block number
            for line in lines:
                if line.strip().startswith("M") or line.strip().startswith("%") or line.strip().startswith("N") or line == "":  # Check for the start/end of the file
                    updated_lines.append(line)  # Keep the "M" line
                elif int(line[:6]) == currentBlock: 
                    updated_lines.append(text_to_insert)
                    block_number += 1
                    updated_line = f"    {block_number:02d}{line[6:]}"  # Update the block number
                    updated_lines.append(updated_line)
                    block_number += 1
                else:
                    updated_line = f"    {block_number:02d}{line[6:]}"  # Update the block number
                    updated_lines.append(updated_line)
                    block_number += 1

                # Join the updated lines into a single string
                updated_text = '\n'.join(updated_lines)

                # Set the updated text back into the QTextEdit
                self.gcode_browser.setPlainText(updated_text)
        else:
            self.errorMessage("You need to enter a block number for insertion position")

    # Mutually exclusive function
    def exclusive_retract_behavior(self, clicked_checkbox, checkboxes):
        for checkbox in checkboxes:
            if checkbox is not clicked_checkbox:
                checkbox.setChecked(False)
    
    # Opens DXF file from your computer
    def openFile(self):
        options = QFileDialog.Options()
        self.file_path, _ = QFileDialog.getOpenFileName(self, "Open DXF File", "", "DXF Files (*.dxf);;All Files (*)", options=options)
        if self.file_path:
            entities = parse_dxf_file(self.file_path)
            self.parseAndDisplayDXF(entities)
           
    # Starts gcode generating process
    def generateGCode(self):
        if self.file_path == "":
            self.errorMessage("You need to insert a DXF first")
        elif self.getStockRadius() == "":
            self.errorMessage("You need to enter a stock radius")
        elif self.getRoughFeed() == "":
            self.errorMessage("You need to enter a roughing feedrate")
        elif self.getFinishFeed() == "":
            self.errorMessage("You need to enter a finishing feedrate")
        elif self.getRoughStep() == "":
            self.errorMessage("You need to enter a stepdown. 0 = 1 pass")
        else:
            entities = parse_dxf_file(self.file_path)
            self.output_code = generate_gcode_from_dxf(entities, self.isUseM3M5Checked(), self.isStartRetractXChecked(), self.isStartRetractZChecked(), self.isStartRetractXZChecked(), self.getStockRadius(), self.getRoughFeed(), self.getRoughStep(), self.getFinishFeed(), self.getFinishStep())
            self.gcode_browser.clear()
            self.gcode_browser.append(''.join(self.output_code))
            
    # Displays DXF and scales uniformly to fit screen
    def parseAndDisplayDXF(self, entities):
        self.scene.clear()
        # Get the drawing extents for scaling
        min_x, min_y, max_x, max_y = calculate_drawing_extents(entities)
        drawing_width = max_x - min_x
        drawing_height = max_y - min_y
        scale_factor = 750 / max(drawing_width, drawing_height)  # Adjust the scale as needed

        # draw line for x axis
        line = self.scene.addLine(0, 0, -750, 0)
        pen = QPen(QColor(255, 0, 0))
        pen.setStyle(Qt.DashLine)  # Set the style to DashLine
        pen.setDashPattern([25, 20])  # Adjust the spacing here
        line.setPen(pen)
        
        # draw DXF entities
        for entity in entities:
            if entity['type'] == 'LINE':
                start_x, start_y = entity['start_point']
                end_x, end_y = entity['end_point']
                line = self.scene.addLine(start_x * scale_factor, -start_y * scale_factor, end_x * scale_factor, -end_y * scale_factor)
                pen = QPen(QColor(0, 0, 255))
                line.setPen(pen)
            elif entity['type'] == 'ARC':
                # Extract ARC data
                center_x, center_y = entity['center_point']
                radius = entity['radius']
                start_angle = entity['start_angle']
                end_angle = entity['end_angle']

                # Calculate scaled values
                center_x_scaled = center_x * scale_factor
                center_y_scaled = -center_y * scale_factor
                radius_scaled = radius * scale_factor

                # Calculate start and end points based on angles and radius
                start_x = center_x + radius * math.cos(math.radians(start_angle))
                start_y = center_y + radius * math.sin(math.radians(start_angle))
                end_x = center_x + radius * math.cos(math.radians(end_angle))
                end_y = center_y + radius * math.sin(math.radians(end_angle))

                start_x_scaled = start_x * scale_factor 
                start_y_scaled = -start_y * scale_factor 
                end_x_scaled = end_x * scale_factor
                end_y_scaled = -end_y * scale_factor

                # Draw the scaled arc using QGraphicsPathItem
                arc_path = QPainterPath()
                arc_path.moveTo(start_x_scaled, start_y_scaled)
                arc_path.arcTo(center_x_scaled - radius_scaled, center_y_scaled - radius_scaled, radius_scaled * 2, radius_scaled * 2, start_angle, (end_angle - start_angle))

                arc = QGraphicsPathItem(arc_path)
                pen = QPen(QColor(0, 0, 255))
                arc.setPen(pen)
                self.scene.addItem(arc)
            elif entity['type'] == 'POLYLINE':
                vertices = entity['vertices']
                polyline = QGraphicsView()
                poly_scene = QGraphicsScene()
                polyline.setScene(poly_scene)
                pen = QPen(QColor(0, 0, 255))
                for i in range(len(vertices) - 1):
                    start_x, start_y = vertices[i]
                    end_x, end_y = vertices[i + 1]
                    line = poly_scene.addLine(start_x * scale_factor, -start_y * scale_factor, end_x * scale_factor, -end_y * scale_factor)
                    line.setPen(pen)
                self.view.setScene(self.scene)

    # Saves gcode file to your computer
    def saveGCode(self):
        if self.gcode_browser.toPlainText() == "":
            self.errorMessage("GCode empty")
        else:
            filename, _ = QFileDialog.getSaveFileName(self, filter="*.cnc")
            if filename:
                f = open(filename, 'w')
                toWrite = ""
                toWrite = toWrite.join(''.join(self.gcode_browser.toPlainText()) )
                f.write(toWrite)
                self.setWindowTitle(str(os.path.basename(filename)) + " - Notepad Alpha")
                f.close()
        
    def errorMessage(self, message):
        self.msg = QMessageBox()
        self.msg.setWindowTitle("Error")
        self.msg.setText(message)
        self.msg.exec_()
       
def main():
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    window = DXFParserGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()