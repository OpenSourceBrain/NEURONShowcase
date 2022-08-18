This folder contains scripts that include procedures provide information about cells in the NEURON hoc format.
After creating/loading a cell, one can call the different procedures to get information about sections of the cell, and about the whole cell too.

For example, to get information about the [L5PC cell here](https://github.com/OpenSourceBrain/L5bPyrCellHayEtAl2011/tree/master/NEURON), one can do something like:

```
load_file("nrngui.hoc")

//=================== creating cell object ===========================
load_file("import3d.hoc")
objref L5PC

strdef morphology_file
morphology_file = "../morphologies/cell1.asc"

load_file("../models/L5PCbiophys3.hoc")
load_file("../models/L5PCtemplate.hoc")
L5PC = new L5PCtemplate(morphology_file)

//=================== get info ===========================

load_file("cellCheck.hoc")
load_file("nCTools.hoc")

// run procedures from cellCheck or nCTools
cellInfo("L5PC")

// print all section names
L5PC.all.printnames()

// select a section
access L5PCtemplate[0].soma[0]

// run section specific function
morph()
```
