#!/usr/bin/env python

import json
import logging
import os
from utlis.common import *
import time

import pandas as pd
from joblib import Parallel, delayed
import distutils.dir_util
import utlis.foldx as foldx
import utlis.io as io
import utlis.rosetta as rosetta
from utlis import abacus
from utlis import judge
from utlis import autofix
import logging

FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
d = {'clientip': '192.168.0.1', 'user': 'grape-fast'}
logger = logging.getLogger('tcpserver')
# logger.warning('Protocol problem: %s', 'connection reset', extra=d)

class GRAPE:
    def __init__(self):
        self.repaired_pdbfile: str
        self.relaxed_prot: str
        self.running_time = {
            "foldx_repair": 0.0,
            "foldx_scan": 0.0,
            "rosetta_relax": 0.0,
            "rosetta_scan": 0.0,
            "abacus_prepare": 0.0,
            "abacus_scan": 0.0,
            "abacus2": 0.0,
            "MD simulations": 0.0,
        }
        self.abacus2_results = {}
        # self.repaired_pdbfile: str
        pass

    def run_foldx(self, pdb, threads, chain, numOfRuns):
        logger.info("FoldX started at %s" % (time.ctime()))
        prot_foldx = foldx.FoldX(pdb, "", threads)
        repair_start = time.time()
        self.repaired_pdbfile = prot_foldx.repairPDB()
        repair_end = time.time()
        repair_time = repair_end - repair_start
        self.running_time["foldx_repair"] = repair_time
        logger.info("FoldX Repair took %f seconds." % (repair_time))

        prot = io.Protein(self.repaired_pdbfile, chain)
        seq, resNumList = io.Protein.pdb2seq(prot)
        distutils.dir_util.mkpath(FOLDX_JOBS_DIR)
        all_results = []
        job_list = []
        for i, res in enumerate(seq):
            resNum = resNumList[i]
            wild = res
            for j, aa in enumerate("QWERTYIPASDFGHKLCVNM"):
                if aa != wild:
                    jobID = FOLDX_JOBS_DIR + "_".join([wild, str(resNum), aa])
                    job_list.append(
                        [
                            self.repaired_pdbfile,
                            wild,
                            chain,
                            aa,
                            resNum,
                            jobID,
                            numOfRuns,
                        ]
                    )
        # print("[INFO]: FoldX started at %s" %(time.ctime()))
        scan_start = time.time()
        Parallel(n_jobs=threads)(delayed(prot_foldx.runOneJob)(var) for var in job_list)
        scan_end = time.time()
        scan_time = scan_end - scan_start
        self.running_time["foldx_scan"] = scan_time
        logger.info("FoldX Scan took %f seconds." % (scan_time))

        return all_results

    def run_rosetta(self, pdb, threads, chain, relax_num, exe, rosettadb):
        logger.info("Rosetta started at %s" % (time.ctime()))
        # relax_num = 200
        prot_rosetta = rosetta.Rosetta(pdb, relax_num, threads, exe, rosettadb)
        relax_start = time.time()
        relaxed_prot = prot_rosetta.relax()
        relax_end = time.time()
        relax_time = relax_end - relax_start
        self.running_time["rosetta_relax"] = relax_time
        logger.info("Rosetta Relax took %f seconds." % (relax_time))

        prot = io.Protein(pdb, chain)
        seq, resNumList = io.Protein.pdb2seq(prot)
        distutils.dir_util.mkpath(ROSETTA_JOBS_DIR)
        # all_results = []
        job_list = []
        for i, res in enumerate(seq):

            resNum = resNumList[i]
            wild = res
            for j, aa in enumerate("QWERTYIPASDFGHKLCVNM"):
                if aa != wild:
                    jobID = ROSETTA_JOBS_DIR + "_".join([wild, str(resNum), aa])
                    job_list.append([wild, aa, str(i + 1), jobID])

        scan_start = time.time()
        Parallel(n_jobs=threads)(
            delayed(prot_rosetta.runOneJob)(var) for var in job_list
        )
        scan_end = time.time()
        scan_time = scan_end - scan_start
        self.running_time["rosetta_scan"] = scan_time
        logger.info("Rosetta cartesian_ddg Scan took %f seconds." % (scan_time))

        return prot_rosetta

    def run_abacus2(self, pdb, threads, chain):

        logger.info("ABACUS2 started at %s" % (time.ctime()))
        distutils.dir_util.mkpath(ABACUS2_JOBS_DIR)
        prot = io.Protein(pdb, chain)
        seq, resNumList = io.Protein.pdb2seq(prot)

        # all_results = {}
        job_list = []
        for i, res in enumerate(seq):
            resNum = resNumList[i]
            wild = res
            for j, aa in enumerate("QWERTYIPASDFGHKLCVNM"):
                if aa != wild:
                    # mutationName = "_".join([wild, str(resNum), aa])
                    # all_results[mutationName] = 0
                    job_list.append(
                        [
                            pdb,
                            wild,
                            chain,
                            aa,
                            resNum
                        ]
                    )
        # print("[INFO]: FoldX started at %s" %(time.ctime()))
        scan_start = time.time()
        abacus2_results = Parallel(n_jobs=threads)(delayed(abacus.runOneJob)(var) for var in job_list)
        # mutations, scores = zip(*result)
        scan_end = time.time()
        scan_time = scan_end - scan_start
        self.running_time["abacus2"] = scan_time
        logger.info("ABACUS2 Scan took %f seconds." % (scan_time))
        # print(self.abacus2_results)
        # ABACUS2_RESULTS_DIR + ABACUS2_SCORE_FILE
        with open(ABACUS2_RESULTS_DIR + ABACUS2_SCORE_FILE, "w+") as complete:
            complete.write(
                "#Score file formatted by GRAPE from ABACUS2.\n#mutation\tscore\tstd\n"
            )
            for pair in abacus2_results:
                complete.write("\t".join([pair[0], str(round(pair[1], 4)), "0"]) + "\n")
            complete.close()

        return self.abacus2_results

    def Analysis_foldx(self, pdb, chain, foldx1):
        self.repaired_pdbfile = pdb.replace(".pdb", "_Repair.pdb")
        distutils.dir_util.mkpath(FOLDX_RESULTS_DIR)
        prot = io.Protein(pdb, chain)
        seq, resNumList = io.Protein.pdb2seq(prot)

        all_results = []
        for i, res in enumerate(seq):
            resNum = resNumList[i]
            wild = res
            for j, aa in enumerate("QWERTYIPASDFGHKLCVNM"):
                # jobID = "foldx_jobs/" + str(i) + "_" + str(j) + "/"
                if aa != wild:
                    jobID = FOLDX_JOBS_DIR + "_".join([wild, str(resNum), aa])
                    all_results.append(
                        foldx1.calScore(wild, resNum, aa, self.repaired_pdbfile, jobID)
                    )

        with open(FOLDX_RESULTS_DIR + FOLDX_SCORE_FILE, "w+") as foldxout:
            foldxout.write(
                "#Score file formatted by GRAPE from FoldX.\n#mutation\tscore\tstd\n"
            )
            for line in all_results:
                foldxout.write("\t".join([line[0], str(line[1]), str(line[2])]) + "\n")
            foldxout.close()

        return all_results

    def Analysis_rosetta(self, pdb, chain, prot_rosetta):
        distutils.dir_util.mkpath(ROSETTA_RESULTS_DIR)
        prot = io.Protein(pdb, chain)
        seq, resNumList = io.Protein.pdb2seq(prot)

        all_results = []
        for i, res in enumerate(seq):
            resNum = resNumList[i]
            wild = res
            for j, aa in enumerate("QWERTYIPASDFGHKLCVNM"):
                if aa != wild:
                    # jobID = "foldx_jobs/" + str(i) + "_" + str(j) + "/"
                    # "_".join([wild, str(resNum), mutation])
                    rosettaddgfile = (
                            ROSETTA_JOBS_DIR
                            + "_".join([wild, str(resNum), aa])
                            + "/mtfile.ddg"
                    )
                    all_results.append(
                        ["_".join([wild, str(resNum), aa])]
                        + prot_rosetta.read_rosetta_ddgout(rosettaddgfile)
                    )

        with open(ROSETTA_RESULTS_DIR + ROSETTA_SCORE_FILE, "w+") as rosettaout:
            rosettaout.write(
                "#Score file formatted by GRAPE from Rosetta.\n#mutation\tscore\tstd\n"
            )
            for line in all_results:
                rosettaout.write(
                    "\t".join([line[0], str(line[1]), str(line[2])]) + "\n"
                )
            rosettaout.close()

        return all_results

    def analysisGrapeScore(self, scoreFile, cutoff, result_dir):
        result_dict = {"mutation": [], "energy": [], "SD": [], "position": []}
        with open(scoreFile, "r") as scorefile:
            for line in scorefile:
                if line[0] != "#":
                    lst = line.strip().split("\t")
                    result_dict["mutation"].append(lst[0].replace("_", ""))
                    result_dict["energy"].append(float(lst[1]))
                    result_dict["SD"].append(float(lst[2]))
                    result_dict["position"].append(int(lst[0].split("_")[1]))
            scorefile.close()
        # print(result_dict)
        CompleteList_df = pd.DataFrame(result_dict)
        CompleteList_SortedByEnergy_df = CompleteList_df.sort_values(
            "energy"
        ).reset_index(drop=True)

        def BetsPerPosition(df):
            position_list = []
            length = df.shape[0]
            for i in range(length):
                if df["position"][i] in position_list:
                    df = df.drop(index=i)
                else:
                    position_list.append(df["position"][i])
            return df.reset_index(drop=True)

        def BelowCutOff(df, cutoff):
            # position_list = []
            length = df.shape[0]
            for i in range(length):
                if float(df["energy"][i]) > float(cutoff):
                    df = df.drop(index=i)
                else:
                    continue
            return df.reset_index(drop=True)

        BestPerPosition_SortedByEnergy_df = BetsPerPosition(
            CompleteList_SortedByEnergy_df
        )
        BestPerPosition_df = BetsPerPosition(CompleteList_SortedByEnergy_df)
        BelowCutOff_df = BelowCutOff(CompleteList_df, cutoff)
        BelowCutOff_SortedByEnergy_df = BelowCutOff(
            CompleteList_SortedByEnergy_df, cutoff
        )
        BestPerPositionBelowCutOff_SortedByEnergy_df = BelowCutOff(
            BestPerPosition_SortedByEnergy_df, cutoff
        )
        BestPerPositionBelowCutOff_df = BelowCutOff(BestPerPosition_df, cutoff)

        def out_tab_file(df, name, result_dir):
            filename = result_dir + "/MutationsEnergies_" + name[:-3] + ".tab"
            with open(filename, "w+") as of:
                of.write(
                    df.to_csv(
                        columns=["mutation", "energy", "SD"], sep="\t", index=False
                    )
                )
                of.close()

        out_tab_file(CompleteList_df, "CompleteList_df", result_dir)
        out_tab_file(
            CompleteList_SortedByEnergy_df, "CompleteList_SortedByEnergy_df", result_dir
        )
        out_tab_file(
            BestPerPosition_SortedByEnergy_df,
            "BestPerPosition_SortedByEnergy_df",
            result_dir,
        )
        out_tab_file(BestPerPosition_df, "BestPerPosition_df", result_dir)
        out_tab_file(BelowCutOff_df, "BelowCutOff_df", result_dir)
        out_tab_file(
            BelowCutOff_SortedByEnergy_df, "BelowCutOff_SortedByEnergy_df", result_dir
        )
        out_tab_file(
            BestPerPositionBelowCutOff_SortedByEnergy_df,
            "BestPerPositionBelowCutOff_SortedByEnergy_df",
            result_dir,
        )
        out_tab_file(
            BestPerPositionBelowCutOff_df, "BestPerPositionBelowCutOff_df", result_dir
        )


def readfasta(fastafile):
    seq = ""
    with open(fastafile) as fasta:
        for line in fasta:
            if line.startswith(">"):
                continue
            else:
                seq += line.strip()
        fasta.close()

    def checkseq(seq):
        for aa in seq:
            if aa in "QWERTYIPASDFGHKLCVNM":
                continue
            else:
                logger.error("Non-canonical amino acids found in sequence!")
                exit()

    checkseq(seq)
    return seq


def selectpdb4md(pdb, softlist):
    distutils.dir_util.mkpath("selectpdb/")
    # try:
    #     os.mkdir("selectpdb")
    # except FileExistsError:
    #     os.system("rm -rf selectpdb")
    #     os.mkdir("selectpdb")
    selected_dict = {"mutation": [], "score": [], "sd": [], "soft": []}
    for soft in softlist:
        with open("%s_results/MutationsEnergies_BelowCutOff.tab" % (soft)) as scorefile:
            for line in scorefile:
                linelist = line.strip().split()
                if linelist[0] != "mutation":
                    selected_dict["mutation"].append(linelist[0])
                    selected_dict["score"].append(linelist[1])
                    selected_dict["sd"].append(linelist[2])
                    selected_dict["soft"].append(soft)
            scorefile.close()
    selected_df = pd.DataFrame(selected_dict)
    selected_df.to_csv("Selected_Mutation.csv")

    for mutation in set(selected_dict["mutation"]):
        mutation = "_".join([mutation[0], mutation[1:-1], mutation[-1]])
        mut_pdb = pdb.replace(".pdb", "_Repair_1_0.pdb")
        # WORKING_DIR = os.getcwd()
        # print(WORKING_DIR)
        # print("%s/selectpdb"%WORKING_DIR)
        os.system(
            f"cp {FOLDX_JOBS_DIR}/%s/%s selectpdb/%s.pdb" % (mutation, mut_pdb, mutation)
        )
        # os.chdir("%s/selectpdb"%WORKING_DIR)

    return selected_dict


def runMD(platform, selected_dict, md_threads=None):
    from utlis import mdrelax
    os.chdir("selectpdb")

    def one_md(mutation):
        # repeat 5 100ps mds
        mutation = "_".join([mutation[0], mutation[1:-1], mutation[-1]])
        mutant = mutation + ".pdb"
        for i in range(5):
            mdrelax.main(mutant, mutation + f"_sample_{i}.pdb", platform)
            os.system(f"rm {mutation}__tip3p.dcd")

    if platform == "CUDA":
        for mutation in set(selected_dict["mutation"]):
            one_md(mutation)
    if platform == "CPU":
        Parallel(n_jobs=md_threads)(delayed(one_md)(mutation) for mutation in set(selected_dict["mutation"]))
    os.system("rm *dcd")
    os.chdir("../")


def main1(args):
    # args = io.Parser().get_args()
    # print(args)

    pdb = args.pdb
    chain = args.chain
    threads = int(args.threads)
    numOfRuns = str(args.numofruns)
    # ratio = args.ratio
    relax_num = args.relax_number
    foldx_cutoff = -float(args.foldx_cutoff)
    rosetta_cutoff = -float(args.rosetta_cutoff)
    abacus_cutoff = -float(args.abacus_cutoff)
    abacus2_cutoff = -float(args.abacus2_cutoff)
    softlist = args.engine
    preset = args.preset
    md = args.molecular_dynamics
    platform = args.platform
    fillloop = args.fill_break_in_pdb
    seqfile = args.sequence
    auto_fix = args.fix_mainchain_missing
    logger.info("Started at %s" % (time.ctime()))

    #
    # WORKING_DIR = os.getcwd()
    # print(WORKING_DIR)

    def checkpdb(pdb, chain, seqfile=None):

        if bool(seqfile) == False:
            from utlis import modeller_loop

            logger.warning("No sequence provided!")
            pdb = modeller_loop.main(pdb, chain)
            # exit()
        else:
            # print("No sequence provided!")
            seq = readfasta(seqfile)
            if judge.main(pdb, chain, seq):  # break found
                if fillloop:
                    from utlis import modeller_loop
                    pdb = modeller_loop.main(pdb, chain, seq)
                    # exit()
                else:
                    # print("PDB check Failed!")
                    logger.warning("Gaps found in your pdb file. PDB check failed. However, the job will continue.")
                    # exit()
            else:
                logger.info("PDB check passed!")
        return pdb

    if args.mode == "test":
        checkpdb(pdb, chain, seqfile)
        exit()

    exe_dict = {"foldx": "", "relax": "", "cartddg": "", "pmut": "", "abacus": "", "abacus2": ""}

    foldx_exe = os.popen("which foldx").read().replace("\n", "")
    exe_dict["foldx"] = foldx_exe
    pmut_scan_parallel_exe = (
        os.popen("which pmut_scan_parallel.mpi.linuxgccrelease")
            .read()
            .replace("\n", "")
    )
    #     rosettadb = "/".join(pmut_scan_parallel_exe.split("/")[:-3]) + "/database/"
    exe_dict["pmut"] = pmut_scan_parallel_exe
    for release in ["", ".static", ".mpi", ".default"]:
        cartesian_ddg_exe = (
            os.popen("which cartesian_ddg%s.linuxgccrelease" % (release))
                .read()
                .replace("\n", "")
        )
        if cartesian_ddg_exe != "":
            exe_dict["cartddg"] = cartesian_ddg_exe
            break
    relax_exe = os.popen("which relax.mpi.linuxgccrelease").read().replace("\n", "")
    rosettadb = os.popen("echo $ROSETTADB").read().replace("\n", "")
    if not rosettadb:
        rosettadb = "/".join(relax_exe.split("/")[:-4]) + "/database/"
    exe_dict["relax"] = relax_exe
    abacus_prep = os.popen("which ABACUS_prepare").read().replace("\n", "")

    exe_dict["abacus"] = abacus_prep

    singleMutation = os.popen("which singleMutation").read().replace("\n", "")
    exe_dict["abacus2"] = singleMutation

    for soft in softlist:
        if soft == "rosetta":
            if exe_dict["relax"] == "":
                logger.error("Cannot find Rosetta: relax.mpi.linuxgccrelease!")
                exit()
            if preset == "slow":
                if exe_dict["cartddg"] == "":
                    logger.error("Cannot find Rosetta: any cartesian_ddg.linuxgccrelease (mpi nor default nor static)!")
                    exit()
            if preset == "fast":
                if exe_dict["pmut"] == "":
                    logger.error("Cannot find Rosetta: pmut_scan_parallel.mpi.linuxgccrelease!")
                    exit()
        else:
            if exe_dict[soft] == "":
                logger.error("Cannot find %s!" % (soft))
                exit()

    mode = args.mode

    grape = GRAPE()
    foldx1 = foldx.FoldX(pdb, foldx_exe, threads)
    rosetta1 = rosetta.Rosetta(pdb, relax_num, threads, cartesian_ddg_exe, rosettadb)

    if mode == "rerun":
        os.system("rm -rf *_jobs")
        os.system("rm -rf *_results")
        os.system("rm -rf *_relax")
        os.system("rm -rf selectpdb")
        mode = "run"

    if mode == "run":

        pdb = checkpdb(pdb, chain, seqfile)

        if auto_fix:
            pdb = autofix.autofix(pdb, [chain])


        # FoldX
        if "foldx" in softlist:
            grape.run_foldx(pdb, threads, chain, numOfRuns)
            grape.Analysis_foldx(pdb, chain, foldx1)

            grape.analysisGrapeScore(
                FOLDX_RESULTS_DIR + FOLDX_SCORE_FILE, foldx_cutoff, FOLDX_RESULTS_DIR
            )
        if preset == "slow":
            if "rosetta" in softlist:
                prot_rosetta = grape.run_rosetta(pdb, threads, chain, relax_num, cartesian_ddg_exe, rosettadb)
                grape.Analysis_rosetta(pdb, chain, prot_rosetta)
                grape.analysisGrapeScore(
                    ROSETTA_RESULTS_DIR + ROSETTA_SCORE_FILE,
                    rosetta_cutoff,
                    ROSETTA_RESULTS_DIR,
                )
        if preset == "fast":
            if "rosetta" in softlist:
                relaxed_pdb = rosetta1.relax()
                distutils.dir_util.mkpath(ROSETTA_JOBS_DIR)
                os.chdir(ROSETTA_JOBS_DIR)
                # try:
                #     os.mkdir("rosetta_jobs")
                #     os.chdir("rosetta_jobs")
                # except FileExistsError:
                #     os.chdir("rosetta_jobs")
                os.system("cp ../%s/%s ./" % (ROSETTA_RELAX_DIR, relaxed_pdb))
                pmut_time = rosetta1.pmut_scan(relaxed_pdb)
                grape.running_time["rosetta_scan"] = pmut_time
                logger.info("Rosetta pmut_scan_parallel took %f seconds." % (pmut_time))
                os.chdir("..")
                distutils.dir_util.mkpath(ROSETTA_RESULTS_DIR)
                os.chdir(ROSETTA_RESULTS_DIR)
                # try:
                #     os.mkdir("rosetta_results")
                #     os.chdir("rosetta_results")
                # except FileExistsError:
                #     os.chdir("rosetta_results")
                #     os.system("rm *")
                rosetta1.pmut_scan_analysis(f"../{ROSETTA_JOBS_DIR}pmut.out")
                os.chdir("..")

                grape.analysisGrapeScore(
                    ROSETTA_RESULTS_DIR + ROSETTA_SCORE_FILE,
                    rosetta_cutoff,
                    ROSETTA_RESULTS_DIR,
                )

                # prot_rosetta = grape.run_rosetta(pdb, threads, chain, relax_num)
                # grape.Analysis_rosetta(pdb, chain, prot_rosetta)
                # grape.analysisGrapeScore('rosetta_results/All_rosetta.score', rosetta_cutoff, "rosetta_results/")
        if "abacus" in softlist:
            abacus_prepare_time, abacus_scan_time = abacus.run_abacus(pdb)
            grape.running_time["abacus_prepare"] = abacus_prepare_time
            grape.running_time["abacus_scan"] = abacus_scan_time

            abacus.parse_abacus_out()
            grape.analysisGrapeScore(
                ABACUS_RESULTS_DIR + ABACUS_SCORE_FILE, abacus_cutoff, ABACUS_RESULTS_DIR
            )

        if "abacus2" in softlist:
            grape.run_abacus2(pdb, threads, chain)
            grape.analysisGrapeScore(
                ABACUS2_RESULTS_DIR + ABACUS2_SCORE_FILE, abacus2_cutoff, ABACUS2_RESULTS_DIR
            )

    if mode == "analysis":
        # FoldX
        if "foldx" in softlist:
            # pdb = pdb.replace(".pdb", "_Repair.pdb")
            grape.Analysis_foldx(pdb, chain, foldx1)
            grape.analysisGrapeScore(
                FOLDX_RESULTS_DIR + FOLDX_SCORE_FILE, foldx_cutoff, FOLDX_RESULTS_DIR
            )
        if preset == "slow":
            if "rosetta" in softlist:
                prot_rosetta = rosetta.Rosetta(pdb, relax_num, threads, cartesian_ddg_exe, rosettadb)
                grape.Analysis_rosetta(pdb, chain, prot_rosetta)
                grape.analysisGrapeScore(
                    ROSETTA_RESULTS_DIR + ROSETTA_SCORE_FILE,
                    rosetta_cutoff,
                    ROSETTA_RESULTS_DIR,
                )
        if preset == "fast":
            if "rosetta" in softlist:
                distutils.dir_util.mkpath(ROSETTA_JOBS_DIR)
                os.chdir(ROSETTA_JOBS_DIR)
                rosetta1.pmut_scan_analysis(f"../{ROSETTA_JOBS_DIR}pmut.out")
                os.chdir("..")
                grape.analysisGrapeScore(
                    ROSETTA_RESULTS_DIR + ROSETTA_SCORE_FILE,
                    rosetta_cutoff,
                    ROSETTA_RESULTS_DIR,
                )
        if "abacus" in softlist:
            # abacus.run_abacus(pdb)
            abacus.parse_abacus_out()
            grape.analysisGrapeScore(
                ABACUS_RESULTS_DIR + ABACUS_SCORE_FILE, abacus_cutoff, ABACUS_RESULTS_DIR
            )
        if "abacus2" in softlist:
            grape.analysisGrapeScore(
                ABACUS2_RESULTS_DIR + ABACUS2_SCORE_FILE, abacus2_cutoff, ABACUS2_RESULTS_DIR
            )

    logger.info(f"Finished calculation in {mode} mode of grape-fast in {time.ctime()}.\n")
    selected_dict = selectpdb4md(pdb, softlist)
    if md:
        # from utlis import mdrelax
        md_start = time.time()

        if platform == "CUDA":
            runMD(platform, selected_dict)

        if platform == 'CPU':
            md_job_num = int(threads) // 2
            runMD(platform, selected_dict, md_job_num)

        md_end = time.time()
        grape.running_time["MD simulations"] = md_end - md_start
        logger.info("All MDs took %f seconds." % (md_end - md_start))

    else:
        logger.info("No MDs!")

    json_running_time = json.dumps(grape.running_time, indent=4)
    with open("timing.json", "w+") as timing:
        timing.write(json_running_time)
        timing.close()


if __name__ == "__main__":
    args = io.Parser().get_args()
    main1(args)
    logger.info("Ended at %s" % (time.ctime()))
