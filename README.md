# EmcoProcessor
Converts DXF files into GCode that runs on a factory Emco 5 CNC lathe.
Intended to use MFI (Mikes Free Interface) to upload files to the machine via RS232.
MFI is also a good verification tool to ensure the code output is what you expect.
This program reflects how I hand program my own lathe and would love to hear 
suggestions on how others are using their machine and would implement things differently.

You can run the file src/dist/EmcoProcessor or set up the Python environment below.
### Python Environments Setup.
### 1. Install requirements.
- Install [Anaconda](https://docs.anaconda.com/anaconda/install/index.html)
- Install [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
### 2. Clone this GitHub repository.
```
git clone https://github.com/connorlowe90/EmcoProcessor
```
### 3. Create and activate a virtual environment using Anaconda.
```
cd EmcoProcessor
conda env create --name [ENV-NAME] -f resources/environment.yml
conda activate [ENV-NAME]
```
### Current Input DXF requirements. PLEASE READ.
- This assumes :
  - Your DXF just depicts the profile you want to cut and not any facing before or after the part. If you do want to add facing, that can easily be done by inserting the line after generating the GCode.
  - The DXF profile needs to be connected from start to end.
  - Needs to be drawn in XY plane with only the radius profile depicted. 
	Draw in the 2nd or 3rd quadrant (machine X is sketch Y, machine Z is sketch X)
	- 2nd = Y positive and X negative quadrant of sketch
	- 3rd = Y negative and X negative quadrant of sketch
  - Your DXF is starting the cut from X0 (z coordinate on the lathe).
  - Any arcs spanning multiple quadrants are split along the centerline of its center point.
    - In fusion, this can easily be done using the sketch break command. 
    - This ensures that the output code is usable on the machine because the Emco 5 Lathe can't interpret arcs greater than 90 deg.
  - The distance from the Y-axis in the sketch (Y0, which is the machine's X-axis) is the distance to the center of your part.
    - Meaning if your part is revolved around the Y axis in fusion it produces your intended part.
    - In other words, you can't draw the profile anywhere in space, it must be accurately represented with respect to the XY origin.
    - Resolution of 0.01mm, anything smaller will be rounded as that is the resolution of the Emco 5 lathe.

### Example sketch in fusion
![imgageprocessing](https://github.com/connorlowe90/EmcoProcessor/blob/master/tests/Test%20Output%20GUI%20Images/exampleFusionSketch.PNG)

### GUI
![imgageprocessing](https://github.com/connorlowe90/EmcoProcessor/blob/master/tests/Test%20Output%20GUI%20Images/gui.PNG)

### Disclaimer

[https://github.com/connorlowe90/EmcoProcessor/blob/master/DISCLAIMER]
