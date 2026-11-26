How it works
tt_um_Zero_Drift_Opamp is a custom-layout zero-drift operational amplifier built on the SkyWater 130 nm (sky130A) process, occupying a 1x2 analog tile footprint. It operates from a single 1.8 V power supply (VDPWR / VGND; the 3.3 V VAPWR rail is not used) with internal on-chip biasing, requiring only three analog pins (INP, INN, OUT) and one digital clock input (clk_in).

To suppress input-referred DC offset voltage, temperature drift, and low-frequency 
1
/
f
 (flicker) noise, the amplifier uses [TODO: specify technique — e.g., chopper stabilisation / auto-zeroing] clocked by an external 1.8 V square wave on ui[0] (clk_in) around a [TODO: specify core op-amp topology — e.g., folded-cascode / two-stage Miller-compensated] core.

Signal path & offset cancellation: [TODO: Briefly describe in 2–3 sentences how clk_in drives the internal switches/phases to modulate or sample-and-cancel the input offset.]
Clocking: The switching clock is supplied externally on dedicated digital input ui[0] (clk_in) at a nominal frequency of [TODO: e.g., 10 kHz – 100 kHz] (clock_hz is set to 0, so the standard Tiny Tapeout clk pin is unused).
Simulated performance (1.8 V supply):
Input-referred DC offset: [TODO: e.g., < X µV]
Open-loop DC gain: [TODO: e.g., X dB]
Unity-gain bandwidth (GBW): [TODO: e.g., X MHz]
Input common-mode range: [TODO: e.g., X V to Y V]
Quiescent current: [TODO: e.g., X µA]
Pinout summary
Pin	Name	Direction / Type	Function
VDPWR / VGND	Power	Supply	1.8 V single supply (VAPWR unused)
ui[0]	clk_in	Digital input (1.8 V)	External zero-drift switching clock
ua[0]	INP	Analog input	Non-inverting input (0 V – 1.8 V)
ua[1]	INN	Analog input	Inverting input (0 V – 1.8 V)
ua[2]	OUT	Analog output	Operational amplifier output
All remaining digital pins (ui[1:7], uo[0:7], uio[0:7]) and analog pins (ua[3:5]) are unused.

How to test
Keep all signals on INP, INN, OUT, and clk_in strictly within the 0 V to 1.8 V (VGND to VDPWR) supply range.

Power-up and clock setup:

Power the Tiny Tapeout demo board at 1.8 V and select the tt_um_Zero_Drift_Opamp project slot.
Drive ui[0] (clk_in) with a 0 V to 1.8 V square wave at [TODO: nominal clock frequency, e.g., 50 kHz] (either from the demo board's RP2040 microcontroller or an external signal generator).
Unity-gain follower & DC offset check:

Short OUT (ua[2]) directly to INN (ua[1]) to configure the amplifier as a unity-gain buffer.
Apply a mid-rail DC voltage (0.9 V) to INP (ua[0]).
Measure OUT and the differential error 
V
OUT
−
V
INP
 with a high-resolution digital multimeter (DMM).
Compare the measured DC offset with clk_in held static (0 V or 1.8 V) versus clocked at the nominal frequency to verify zero-drift offset reduction.
Closed-loop gain & common-mode sweep:

Connect an external resistive feedback network between OUT (ua[2]), INN (ua[1]), and a 0.9 V mid-rail reference (for example, a non-inverting gain of 10× or 100× using 10 kΩ and 100 kΩ / 1 MΩ resistors) to amplify the residual offset for easier measurement and verify closed-loop linearity.
Sweep the DC voltage on INP (ua[0]) across [TODO: target common-mode range, e.g., 0.3 V – 1.5 V] and record OUT to verify input common-mode range and output swing.
AC frequency response & transient behaviour:

Inject a small-signal sine wave or square-wave step (10–50 mV peak-to-peak biased at 0.9 V DC) into the closed-loop circuit and probe OUT (ua[2]) on an oscilloscope to measure closed-loop bandwidth, slew rate, and settling time.
External hardware
Testing uses the standard Tiny Tapeout demo board with its analog pin header exposed, along with basic lab instruments and passives:

Carrier board: Tiny Tapeout demo board supplying the 1.8 V VDPWR rail (the on-board RP2040 can also be used to generate the 1.8 V clk_in square wave on ui[0]).
Signal sources:
Precision DC voltage source or DAC (for the 0.9 V mid-rail reference and input DC sweeps).
Function generator (for AC sine/step input stimuli, and for clk_in if not driven by the RP2040).
Passive components (breadboard / breakout):
Matched feedback resistors (e.g., 10 kΩ and 100 kΩ / 1 MΩ, 0.1%–1% tolerance) for closed-loop gain testing.
Optional load capacitor ([TODO: e.g., 10 pF – 100 pF]) or output RC low-pass filter to attenuate switching ripple during DC measurements.
Measurement equipment:
High-resolution digital multimeter (5.5-digit or better) for microvolt/millivolt DC offset readings.
