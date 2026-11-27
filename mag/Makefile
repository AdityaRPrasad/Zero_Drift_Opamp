TOP = tt_um_Zero_Drift_Opamp
MAGIC = magic -dnull -noconsole

.PHONY: import_gds drc extract clean

import_gds:
	$(MAGIC) gds_to_mag.tcl

drc:
	$(MAGIC) drc_check.tcl

extract:
	$(MAGIC) -T sky130A << 'MAGIC_EOF'
	load $(TOP)
	extract all
	ext2spice lvs
	ext2spice -o $(TOP).lvs.spice
	quit -noprompt
	MAGIC_EOF

clean:
	rm -f *.ext *.nodes *.sim *.lvs.spice
