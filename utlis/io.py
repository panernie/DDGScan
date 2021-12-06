#!/usr/bin/env python

# By Jinyuan Sun, Oct, 12, 2021
import argparse


class Protein:
    def __init__(self, pdbname, chain):
        self.pdbname = pdbname
        self.chain = chain
        self.seq = ""
        self.resNumList = []

    def _3_2_1(self, x):
        d = {
            "CYS": "C",
            "ASP": "D",
            "SER": "S",
            "GLN": "Q",
            "LYS": "K",
            "ILE": "I",
            "PRO": "P",
            "THR": "T",
            "PHE": "F",
            "ASN": "N",
            "GLY": "G",
            "HIS": "H",
            "LEU": "L",
            "ARG": "R",
            "TRP": "W",
            "ALA": "A",
            "VAL": "V",
            "GLU": "E",
            "TYR": "Y",
            "MET": "M",
        }
        y = d[x]
        return y

    def pdb2seq(self):
        with open(self.pdbname) as pdbfile:
            for line in pdbfile:
                if "ATOM" == line[0:6].replace(" ", ""):
                    if self.chain == line[21].replace(" ", ""):
                        if line[12:16].replace(" ", "") == "CA":
                            if line[16] == "B":
                                continue
                            else:
                                self.seq += self._3_2_1(line[17:20].replace(" ", ""))
                                self.resNumList.append(
                                    int(line[22:26].replace(" ", ""))
                                )
        pdbfile.close()
        return self.seq, self.resNumList


class Parser:
    def __init__(self):
        pass

    def get_args(self):
        parser = argparse.ArgumentParser(
            description="Run FoldX, Rosetta and ABACUS for in silico deep mutation scan."
        )
        parser.add_argument("-pdb", "--pdb", help="Input PDB")
        parser.add_argument(
            "-chain", "--chain", help="Input PDB Chain to do in silico DMS", default="A"
        )
        parser.add_argument(
            "-fill", "--fill_break_in_pdb", help="Use modeller to fill missing residues in your pdb file. Use this option with caution!", default=False
        )
        parser.add_argument(
            "-seq", "--sequence", help="The exact sequence of protein you want to design. All mutation will be named according to this sequence.", default=""
        )
        parser.add_argument(
            "-cpu",
            "--threads",
            help="Number of threads to run FoldX, Rosetta",
            default=16,
        )

        # parser.add_argument("-r", '--ratio', help="Select by ratio mode",default=False)

        parser.add_argument(
            "-fc", "--foldx_cutoff", help="Cutoff of FoldX ddg(kcal/mol)", default=1.5
        )
        parser.add_argument(
            "-rc", "--rosetta_cutoff", help="Cutoff of Rosetta ddg(R.E.U.)", default=5
        )
        parser.add_argument(
            "-ac", "--abacus_cutoff", help="Cutoff of ABACUS SEF(A.E.U.)", default=3
        )
        parser.add_argument(
            "-nstruct",
            "--relax_number",
            help="Number of how many relaxed structure",
            default=50,
        )
        parser.add_argument(
            "-nruns",
            "--numofruns",
            help="Number of runs in FoldX BuildModel",
            default=5,
        )
        parser.add_argument(
            "-sl",
            "--softlist",
            help="List of Software to be used in ddg calculations",
            default="FoldX,Rosetta,abacus",
        )
        parser.add_argument("-mode", "--mode", help="Run, Rerun or analysis", default='run')
        parser.add_argument("-preset", "--preset", help="Fast or Slow", default='slow')
        parser.add_argument(
            "-md",
            "--molecular_dynamics",
            help="Run 1ns molecular dynamics simulations for each mutation using openmm.",
            default=False,
        )
        parser.add_argument(
            "-platform", "--platform", help="CUDA or CPU", default="CUDA"
        )

        args = parser.parse_args()

        return args


if __name__ == "__main__":
    pdbname = "6JTT.pdb"
    chain = "A"
    prot = Protein(pdbname, chain)
    seq, resNumList = Protein.pdb2seq(prot)
    print(seq, resNumList)
