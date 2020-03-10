import sys
from Bio import SeqIO
import tempfile
import os
import glob
import fnmatch
import shutil
import pandas as pd
from collections import defaultdict

from . import rampart

# extract with constraints:
#   -- only one group ever
#   -- only one flowcell ID ever
#   -- always unique read ID

def run(parser, args):
	if not args.directory:
        	directories = os.listdir(args.run_directory)
        	directories = [args.run_directory+'/'+d for d in directories if os.path.isdir(args.run_directory+'/'+d)]
        	args.directory = [rampart.chooser(directories)]

	if isinstance(args.directory, list) and len(args.directory) > 1 and not args.prefix:
		print("Must supply a prefix if gathering multiple directories!", file=sys.stderr)
		raise SystemExit

	if args.prefix:
		prefix = args.prefix
	else:
		prefix = os.path.split(args.directory[0])[-1]

	all_fastq_outfn = "%s_all.fastq" % (prefix)
	all_fastq_outfh = open(all_fastq_outfn, "w")

	summary_files = []

	fastq = defaultdict(list)
	for directory in args.directory:
		d = directory

		for root, dirs, files in os.walk(d):
			paths = os.path.split(root)
			barcode_directory = paths[-1]

			fastq[barcode_directory].extend([root+'/'+f for f in files if f.endswith('.fastq')])
			summary_files.extend([root+'/'+f for f in files if fnmatch.fnmatch(f, '*cing_summary*txt')])

	for barcode_directory, fastq in list(fastq.items()):
		if len(fastq):
			fastq_outfn = "%s_%s.fastq" % (prefix, barcode_directory)
			outfh = open(fastq_outfn, "w")
			print("Processing %s files in %s" % (len(fastq), barcode_directory), file=sys.stderr)

			dups = set()
			uniq = 0
			total = 0	
			for f in fastq:
				for rec in SeqIO.parse(open(f), "fastq"):
					if args.max_length and len(rec) > args.max_length:
						continue
					if args.min_length and len(rec) < args.min_length:
						continue

					total += 1
					if rec.id not in dups:
						SeqIO.write([rec], outfh, "fastq")
						SeqIO.write([rec], all_fastq_outfh, "fastq")

						dups.add(rec.id)
						uniq += 1

			outfh.close()

			print("%s\t%s\t%s" % (fastq_outfn, total, uniq))

	all_fastq_outfh.close()

	print("Found the following summary files:\n", file=sys.stderr)
	for summaryfn in summary_files:
		print ("  " + summaryfn, file=sys.stderr)

	dfs = []

	summary_outfn = "%s_sequencing_summary.txt" % (prefix)
	summaryfh = open(summary_outfn, "w")

	for summaryfn in summary_files:
		df = pd.read_csv(summaryfn, sep="\t")
		# support for local basecalling
		if 'filename_fast5' in df.columns:
			df['filename'] = df['filename_fast5']	
		dfs.append(df)

	pd.concat(dfs).to_csv(summaryfh, sep="\t", index=False)
	summaryfh.close()


