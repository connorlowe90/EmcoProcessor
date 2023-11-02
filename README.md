# EmcoProcessor
Converts DXF files into gcode that runs on a factory Emco 5 CNC lathe

### Python Environments Setup
### 1. Install requirements
- Install [Anaconda](https://docs.anaconda.com/anaconda/install/index.html)
- Install [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
### 2. Clone this GitHub repository
```
git clone https://github.com/connorlowe90/EmcoProcessor
```
### 3. Create and activate a virtual environment using Anaconda
```
cd EmcoProcessor
conda env create --name [ENV-NAME] -f environment.yml
conda activate [ENV-NAME]
```
### Current Input DXF requirements
- Needs to be drawn in XY plane with only the radius profile depicted
![imgageprocessing](https://github.com/connorlowe90/EmcoProcessor/blob/master/Test%20Output%20GUI%20Images/test%20taper%20dxf%20display2.PNG)
