# Codes for FoldX towards Stable Proteins

### See [GUI](GUI/) for the GUI plugin of foldx.

### Installation
First of all, please make sure you have added the FoldX executable to your environment!  
To install it, simplely clone this repo and add it to PATH:
```bash
git clone https://github.com/JinyuanSun/Codes_for_FoldX.git &&
cd Codes_for_FoldX && export PATH="$(pwd):$PATH"
```
### Quickstart
You may want to try it out on a small protein like [Gb1](https://www.rcsb.org/structure/1PGA):
```bash
wget https://files.rcsb.org/download/1PGA.pdb
parallel_single_scan.py -pdb 1PGA.pdb -chain A -sl "FodlX,Rosetta" -mode run -cpu 40
```
You should expecting outputs like:  
A folder named `foldx_results` containing:
```
All_FoldX.score
MutationsEnergies_BestPerPositionBelowCutOff_SortedByEnergy.tab
MutationsEnergies_BelowCutOff.tab
MutationsEnergies_BestPerPosition_SortedByEnergy.tab
MutationsEnergies_BelowCutOff_SortedByEnergy.tab
MutationsEnergies_CompleteList.tab
MutationsEnergies_BestPerPosition.tab
MutationsEnergies_CompleteList_SortedByEnergy.tab
MutationsEnergies_BestPerPositionBelowCutOff.tab
```
And another folder named `foldx_jobs` contains many subdirectories, in each subdirectory, containing raw output for every mutation built by FoldX.
### Inspect structures
Using `scripts/inspectmutation.py` to inspect mutations in pymol:
```bash
pymol inspectmutation.py $Wildtype_structure $Mutation_structure $Mutation_position $Chain
```
### 如果你在中国大陆地区，可以使用`Gitee`:
```bash
git clone https://gitee.com/puzhunanlu30/Codes_for_FoldX.git
```
