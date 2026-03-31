3 Physical Layer




3 Physical Layer


3.1 Overview
The physical layer interfaces to the data link layer for data exchange and connects to the peer UBPU
through serializer/deserializer (SerDes). It consists of the physical coding sublayer (PCS), physical
medium attachment (PMA), and link state management.




                                  Figure 3-1 Physical layer architecture

The PCS performs forward error correction (FEC) encoding/decoding and scrambling. In the TX
direction, it receives data from the data link layer, performs FEC encoding and scrambling, and sends
the processed data to the PMA. In the RX direction, it receives data from the PMA, performs FEC
decoding and descrambling, and sends the data to the data link layer.

The PMA receives and transmits bit streams over SerDes, recovers clocks, modulates signals,
performs Gray coding, precoding, and parallel-to-serial conversion. It SHALL allow the PCS to connect
to multiple physical links in a medium-independent interface.

Link state management implements link training and error recovery by using the link management state
machine (LMSM) to negotiate the data rate, link width, equalization parameters, and encoding mode at
both ends of a link. Once link training is completed, the physical layer enables data exchange for the
data link layer.

The UB physical layer has the following features:

      ⚫    Supports custom data rates to fully utilize the SerDes and channel capabilities.
      ⚫    Supports multiple FEC modes and dynamic FEC mode switching to match the bit error rate
           (BER) characteristics of different links and reduce latency.
      ⚫    Supports fault-tolerant link operation with lane/data rate degradation, optical channel
           protection, and enhanced link resilience.
      ⚫    Supports asymmetric TX/RX link width for power optimization.



unifiedbus.com                                                                                           17
3 Physical Layer



3.1.1 Port, Lane, and Link
A port consists of a TX and a RX. The local TX connects to the peer RX, and the local RX connects to
the peer TX, forming a full-duplex link. Each TX or RX contains one or more lanes, where a lane is a
pair of high-speed differential signal lines. A UBPU port connects to its peer via multiple bidirectional
lanes, to create a high-speed link. The physical layer supports both electrical and optical interconnects.

Each TX or RX SHALL support 1, 2, 4, or 8 lanes. The physical layer SHALL support both symmetric
and asymmetric link configurations. In an asymmetric configuration, the number of TX lanes at one port
may differ from the number of RX lanes. The figure below illustrates an example where Port A has M TX
lanes and N RX lanes. The value of M may be equal to or different from that of N.




                                        Figure 3-2 UB link structure

Asymmetric link widths SHALL be configurable at system initialization. Additionally, the number of active
lanes in each direction may be dynamically adjusted during link operation without disrupting data
transfer on the remaining lanes.


3.1.2 Physical Layer Modes
The physical layer supports two modes: PHY Mode-1 and PHY Mode-2.

                                 Table 3-1 Physical layer operating modes
 Mode                     PHY Mode-1                               PHY Mode-2
 Data Rate (Gbit/s)       4.0 or custom data rates                 2.578125, 25.78125, 53.125, 106.25
                          NRZ: 4.0 Gbit/s                          NRZ: 2.578125 or 25.78125 Gbit/s
 Modulation Mode
                          NRZ or PAM4: custom data rates           PAM4: 53.125 or 106.25 Gbit/s




unifiedbus.com                                                                                              18
3 Physical Layer



The selected mode SHALL be configured prior to system power-on and SHALL NOT be changed during
operation.

The UB physical layer has the following electrical characteristics:

      ⚫      For DAC cables, backplanes, and retimed optical modules, refer to IEEE Std 802.3™-2022
             and IEEE Std 802.3ck™-2022 to check electrical characteristics of data rates in PHY Mode-2.
      ⚫      For non-retimed linear optical components, refer to OIF CEI-112G-LINEAR-PAM4 to check
             the electrical characteristics of the 106.25 Gbit/s rate.
      ⚫      The maximum supported data rate is 118 Gbit/s per lane.
      ⚫      The maximum insertion loss (bump-to-bump, at Nyquist frequency) SHALL be: 40 dB in
             backplane applications and 42 dB in DAC cable applications.

Ports supporting custom data rates SHALL pre-configure the data rate and modulation mode before
shipping. Both ends of the link SHALL support identical data rates and modulation settings.


3.2 Physical Coding Sublayer

3.2.1 Datapath Overview
The datapath at the physical layer includes the PCS and PMA. In the TX direction, the PCS SHALL:

      ⚫      Receive data streams from the data link layer
      ⚫      Optionally apply FEC encoding (bypass mode available)
      ⚫      Scramble the data stream
      ⚫      Apply Gray coding (required for PAM4 modulation)
      ⚫      Apply precoding
      ⚫      Insert alignment marker control (AMCTL) blocks for lane alignment and control (see Section 3.2.4)
      ⚫      Forward the processed bit stream to the PMA

In the RX direction, the PCS performs the reverse sequence of operations to reconstruct the data stream.




unifiedbus.com                                                                                              19
3 Physical Layer




                                     Figure 3-3 Datapath functions

FEC bypass means to skip FEC encoding and decoding. Data striping occurs in the TX, that is, data is
distributed as symbols in an interleaved manner across lanes. The reverse operation, data destriping,
occurs in the RX.




unifiedbus.com                                                                                          20
3 Physical Layer



3.2.2 TX Functions

3.2.2.1 Forward Error Correction

Reed-Solomon (RS) codewords are used in the PCS for encoding. They operate within a finite field.
The encoder encodes the received K FEC message symbols, generates N-K parity symbols, and forms
N RS FEC symbols to produce RS(N, K, T) FEC codewords.

The RS FEC encoder operates within the finite field GF 2        ( ) , where m is the number of bits contained
                                                                   m


in each RS FEC symbol.

Generator polynomial g ( x) of RS FEC codewords:
                                   2𝑇−1

                          𝑔(𝑥) = ∏ (𝑥 − 𝛼 𝑗 ) = 𝑔2𝑇 𝑥 2𝑇 + 𝑔2𝑇−1 𝑥 2𝑇−1 +. . . +𝑔1 𝑥 + 𝑔0
                                    𝑗=0

 is the root of the primitive polynomial of GF ( 2m ) . For the GF ( 28 ) finite field, the primitive
polynomial is  =x8 +x4 +x3 +x2 +1 .

Message polynomial m( x) of RS FEC codewords:

                             𝑚(𝑥) = 𝑚𝐾−1 𝑥 𝑁−1 + 𝑚𝐾−2 𝑥 𝑁−2 +. . . +𝑚1 𝑥 2𝑇+1 + 𝑚0 𝑥 2𝑇

𝑚𝑖 = 𝑚𝑖,7 𝛼 7 + 𝑚𝑖,6 𝛼 6 +. . . +𝑚𝑖,1 𝛼 + 𝑚𝑖,0 is the ith message symbol, and is input to RS FEC encoder in
the sequence of 𝑚𝐾−1 , 𝑚𝐾−2 , . . . , 𝑚1 , 𝑚0 .

The RS FEC parity polynomial p( x) is as follows. The coefficients are 𝑝2𝑇−1 , 𝑝2𝑇−2 , . . . , 𝑝0 .

                                 𝑝(𝑥) = 𝑝2𝑇−1 𝑥 2𝑇−1 + 𝑝2𝑇−2 𝑥 2𝑇−2 +. . . +𝑝1 𝑥 + 𝑝0

The parity polynomial is produced by dividing the message polynomial 𝑚(𝑥) by the generator
polynomial 𝑔(𝑥) and taking the remainder.

The following figure shows the RS FEC encoder circuit.




                                          Figure 3-4 RS FEC encoder circuit

The symbols after RS FEC encoding are in the sequence of mK-1, mK-2,..., m0, p2T-1,..., p0.

The following table lists the coefficients of the generator polynomial of the FEC encoder.




unifiedbus.com                                                                                                21
3 Physical Layer



                          Table 3-2 Generator polynomial coefficients gi (decimal)
     i           0        1          2          3         4           5           6     7            8
    gi          24       200       173         239        54         81        11      255           1


UB supports FEC working within the finite field GF(28). Based on correction capabilities, there are two
modes: RS (128,120,T=4) and RS (128,120,T=2), which can correct four symbols and two symbols,
respectively.

During encoding, the generation method and values of the eight parity symbols in RS (128,120, T=2)
mode are the same as those in RS (128,120, T=4) mode.

If FEC is enabled, the TX and RX SHALL use the same mode.

By default, the PCS supports RS (128,120,T=4) FEC mode and allows for mode negotiation during link
training and dynamic mode switching during normal operations.

The following table lists RS FEC codewords.

                                         Table 3-3 RS FEC codewords
 FEC Mode                                       N              K              T              m
 RS (128,120,T=2)                               128            120            2              8
 RS (128,120,T=4)                               128            120            4              8


3.2.2.2 Pre-FEC Distribution

The following shows the pre-FEC distribution rules, where mA and mB represent the message symbols of
different FEC encoders. Each FEC encoder contains K message symbols. i = (0 : K-1) represents the index
of an RS FEC message symbol. Each FEC symbol contains m bits. For RS (128,120), K = 120, m = 8.

The PCS supports either one non-interleaved FEC encoder or two interleaved FEC encoders.

Data from the data link layer can be considered as a serial data stream (tx_data). If two FEC encoders
are used, data streams are interleaved and distributed at the granularity of RS FEC symbol. In the
following formulas, CodecNum represents the number of encoders.

         ⚫   CodecNum = 1 (non-interleaved FEC):
             mA<K-1-i> = tx_data<(m*i+m-1): (m*i)>
         ⚫   CodecNum = 2 (interleaved FEC):
             mA<K-1-i> = tx_data<(2m*i+m-1): (2m*i)>
             mB<K-1-i> = tx_data<(2m*i+2m-1): (2m*i+m)>




unifiedbus.com                                                                                            22
3 Physical Layer



3.2.2.3 Post-FEC Distribution

CA and CB are codeword outputs from different FEC encoders. Each FEC codeword contains N FEC
symbols (for RS (128,120), N = 128). Lane<j,i> represents the ith symbol distributed by an encoder to
lane j, and LaneNum represents the number of lanes included in the TX.

FEC symbol distribution rules:

      ⚫   CodecNum = 1 (non-interleaved):
          for i=0 to (N/LaneNum-1)
              for j=0 to (LaneNum-1)
                   Lane<j,i> = CA<(N-1)-i*LaneNum-j>
      ⚫   CodecNum = 2 (interleaved):
          −   if LaneNum=1:

                   for i=0 to (N*2-1)

                       if i mod 2 = 0

                            Lane<0,i> = CA<(N-1)-i/2>

                       if i mod 2 = 1

                            Lane<0,i> = CB<(N-1)-(i-1)/2>

          −   if LaneNum=2/4/8:

                   for i=0 to (N*2/LaneNum-1)

                       for j=0 to (LaneNum/2-1)

                            if i mod 2 = 0

                                 Lane<j*2,i> = CA<(N-1)-i*(LaneNum/2)-j>

                                 Lane<j*2+1,i> = CB<(N-1)-i*(LaneNum/2)-j>

                            if i mod 2 = 1

                                 Lane<j*2,i> = CB<(N-1)-i*(LaneNum/2)-j>

                                 Lane<j*2+1,i> = CA<(N-1)-i*(LaneNum/2)-j>




unifiedbus.com                                                                                          23
3 Physical Layer



The figures below show the post-FEC symbol distribution of RS (128,120). CA and CB are codewords
output by different FEC encoders. Each FEC codeword contains 128 symbols, including 120 message
symbols (m119 to m0) and 8 parity symbols (p7 to p0).

Non-interleaved distribution of FEC symbols on x8 lanes




                   Figure 3-5 Non-interleaved distribution of post-FEC symbols to x8 lanes




unifiedbus.com                                                                                     24
3 Physical Layer



Interleaved distribution of FEC symbols on x8 lanes




                    Figure 3-6 Interleaved distribution of post-FEC symbols to x8 lanes


3.2.2.4 Scrambling

Scrambling is essential to enhance the electrical performance of links.

Per-lane additive scrambling is used, and scrambling seeds SHALL be synchronized on both TX and RX.

Scrambling seed values can be obtained based on lane IDs carried in the AMCTL.

These are the scrambling rules for both TX and RX, which SHALL be identical:

    ⚫    All symbols of the exit electrical idle block (EEIB) are not scrambled.
    ⚫    All symbols of the AMCTL are not scrambled.
    ⚫    All symbols of the link training block (LTB) SHALL be scrambled.
    ⚫    All data from the data link layer SHALL be scrambled. For symbols that need to be scrambled
         or descrambled, the least significant bit (LSB) is scrambled/descrambled first and the most
         significant bit (MSB) is scrambled/descrambled last.
    ⚫    Scrambling seeds SHALL be reset when an AMCTL with end of data flit (AMCTL with EDF) is
         received when LMSM is not in Send_NullBlock or Link_Active state (see Section 3.4.3.6 and
         Section 3.4.3.7). Scrambling seeds SHALL not be reset when an AMCTL with start of data flit
         (AMCTL with SDF) is received when LMSM is in Send_NullBlock or Link_Active state.




unifiedbus.com                                                                                         25
3 Physical Layer



3.2.3 RX Functions

3.2.3.1 Frame Lock and Lane Alignment

The RX receives bit streams on a per-lane basis, with each lane generating its data stream according to
the bit reception sequence. The AMCTL is first locked in the PCS (see Section 3.2.4.4), and the RX
then leverages AMCTL's periodic insertion pattern to enable detection and locking.

After AMCTL locking, the RX aligns lanes based on the position of AMCTL with SDF received on each
lane to eliminate skew between lanes. The following table lists the maximum skew supported by the
PCS for different data rates.

                     Table 3-4 Maximum skew between RX lanes at different data rates
 Data Rate (Gbit/s)             4.0          2.578125           25.78125      53.125          106.25
 Maximum Skew (ns)              20           10                 10            8               6

Note: The maximum skew at custom data rates SHALL be defined by vendors.


3.2.3.2 Descrambling

The RX descrambles data based on scrambling rules. Except for the AMCTL and EEIB, all other
symbols SHALL be input into the descrambling circuit to restore the original data.


3.2.3.3 Reordering

The receive sequence of PCS lanes may differ from the transmit sequence. The AMCTL includes the
lane ID (AMCTL.LID) for each data stream. The RX reorders the data sequences using the AMCTL.LID
and assigns them to their respective PCS lanes.

The AMCTL.LID is used for lane reordering only when full out-of-order occurs.

The full out-of-order means that lanes 0 to N are not arranged in the sequence of {0, 1, 2,..., N} or {N,...,
2, 1, 0}, or lane 0 is not in the physical lane positions of {0, 1, 3, 7}.


3.2.3.4 Deinterleaving

Once all streams are deskewed and reordered, the PCS—if FEC is enabled—distributes the received
data to different FEC decoders for decoding based on the number of FEC decoders.


3.2.3.5 FEC Decoding

An RS FEC decoder receives a complete FEC frame based on the FEC codeword length, performs
error correction and decoding, and deletes the parity bits inserted by the TX. (For RS (128, 120), a
complete FEC frame SHALL contain 128 symbols.)

In RS (128,120,T = 4) mode, the polynomial corresponding to the 128 symbols received by the RX is
r(x)=r_127∙x^127+r_126∙x^126+...+r_1∙x+r_0, where r_i represents the ith symbol (0 ≤ i ≤ 127), r_127




unifiedbus.com                                                                                            26
3 Physical Layer



represents the first received symbol, and r_0 represents the latest received symbol. In a decoding
process, eight parity symbols are first calculated, that is, the jth parity symbol S_j is calculated by using
the formula S_j=r(α^j ) (0 ≤ j < 8).

In RS(128,120,T = 2), four parity symbols S_j=r(α^j ) (0 ≤ j < 4) are calculated by the RX, and four parity
symbols S_j=r(α^j ) (4 ≤ j < 8) are used to verify whether errors are corrected after decoding.

If the number of error symbols in codewords is less than or equal to T, the RS FEC decoder SHALL
fully correct them. If the number is greater than T, the RS FEC decoder SHALL report a failure
indicating that the number of error symbols has been exceeded, to recognize the FEC decoding failure.
If FEC decoding fails, the data link layer's retransmission mechanism is triggered. If retransmission
fails, the LMSM enters the Retrain state.

FEC decoders MAY support link quality monitoring. Once enabled, an error symbol counter tracks
statistics related to FEC decoding failures. When any FEC decoder detects that the number of error
symbols surpasses its error correction capability, the error counter increases by T + 1 upon each FEC
decoding failure. The counter SHALL collect error symbols of all FEC decoders. The variable
hi_FEC_BER can be used to indicate link quality. It is set to 1 if error symbols exceed the defined
threshold (which is implementation-specific), signaling week FEC capability and prompting the system
to adjust the FEC mode. When no errors occur over a prolonged period (implementation-specific), it
represents strong link quality/robust FEC capability. The system MAY then switch to a lightweight FEC
mode or FEC bypass.


3.2.3.6 Post-FEC Interleaving

The data output from FEC decoders is interleaved and combined into a data stream using m-bits
chunks to restore the original transmission stream and send it to the data link layer. Here, m represents
the number of bits contained in each RS FEC symbol. (For RS (128,120), m = 8.)


3.2.4 Alignment Marker Control
The alignment marker control (AMCTL) of the UB physical layer is used for frame alignment and
extended control functions, including:

    ⚫    Frame alignment of each lane
    ⚫    Lane ID identification
    ⚫    Dynamic link width switching control
    ⚫    AMCTL insertion period control
    ⚫    AMCTL with SDF
    ⚫    AMCTL with EDF
    ⚫    FEC control
    ⚫    Enter electrical idle (EEI)

The PCS SHALL periodically insert the AMCTL per lane in the TX direction.




unifiedbus.com                                                                                             27
3 Physical Layer



3.2.4.1 eBCH-16 Encoding

The AMCTL falls outside the scope of FEC protection and thus SHALL require separate encoding with
error detection and correction capabilities.

It is encoded using eBCH-16, which stands for extended Bose-Chaudhuri-Hocquenghem (eBCH) encoding.

Each eBCH-16 codeword offers the following capabilities:

    ⚫     Detect 7-bit errors.
    ⚫     Correct any 3-bit random errors and partial 4-bit random errors.

Each eBCH-16 codeword consists of BCH (15, 5) and 1-bit even parity. In BCH (15, 5), the payload is 5
bits, while the total code length is 15 bits. Its generator polynomial is represented as
g BCH (15,5) ( x ) = x10 + x8 + x5 + x 4 + x 2 + x + 1 .
Each eBCH-16 codeword contains 16 bits, which are divided into Byte_A and Byte_B.




                                        Figure 3-7 eBCH-16 codeword format

There are 32 eBCH codewords in total, and the Hamming distance between any two codewords is 8.

                                         Table 3-5 eBCH (16, 5) codeword set

                                 Byte_A                                                  Byte_B

         Bit7   Bit6    Bit5   Bit4    Bit3   Bit2   Bit1   Bit0   Bit7   Bit6   Bit5   Bit4   Bit3   Bit2   Bit1   Bit0

 CW0       0      0      0       0      0       0      0     0      0      0      0      0      0      0      0      0

 CW1       0      0      0       0      1       0      1     0      0      1      1      0      1      1      1      1

 CW2       0      0      0       1      0       1      0     0      1      1      0      1      1      1      0      1

 CW3       0      0      0       1      1       1      1     0      1      0      1      1      0      0      1      0

 CW4       0      0      1       0      0       0      1     1      1      1      0      1      0      1      1      0

 CW5       0      0      1       0      1       0      0     1      1      0      1      1      1      0      0      1

 CW6       0      0      1       1      0       1      1     1      0      0      0      0      1      0      1      1

 CW7       0      0      1       1      1       1      0     1      0      1      1      0      0      1      0      0

 CW8       0      1      0       0      0       1      1     1      1      0      1      0      1      1      0      0

 CW9       0      1      0       0      1       1      0     1      1      1      0      0      0      0      1      1

CW10       0      1      0       1      0       0      1     1      0      1      1      1      0      0      0      1

CW11       0      1      0       1      1       0      0     1      0      0      0      1      1      1      1      0

CW12       0      1      1       0      0       1      0     0      0      1      1      1      1      0      1      0

CW13       0      1      1       0      1       1      1     0      0      0      0      1      0      1      0      1




unifiedbus.com                                                                                                           28
3 Physical Layer



                              Byte_A                                                  Byte_B

        Bit7   Bit6   Bit5   Bit4   Bit3   Bit2   Bit1   Bit0   Bit7   Bit6   Bit5   Bit4   Bit3   Bit2   Bit1   Bit0

CW14     0       1     1      1      0      0      0      0      1      0      1      0      0      1      1      1

CW15     0       1     1      1      1      0      1      0      1      1      0      0      1      0      0      0

CW16     1       0     0      0      0      1      0      1      0      0      1      1      0      1      1      1

CW17     1       0     0      0      1      1      1      1      0      1      0      1      1      0      0      0

CW18     1       0     0      1      0      0      0      1      1      1      1      0      1      0      1      0

CW19     1       0     0      1      1      0      1      1      1      0      0      0      0      1      0      1

CW20     1       0     1      0      0      1      1      0      1      1      1      0      0      0      0      1

CW21     1       0     1      0      1      1      0      0      1      0      0      0      1      1      1      0

CW22     1       0     1      1      0      0      1      0      0      0      1      1      1      1      0      0

CW23     1       0     1      1      1      0      0      0      0      1      0      1      0      0      1      1

CW24     1       1     0      0      0      0      1      0      1      0      0      1      1      0      1      1

CW25     1       1     0      0      1      0      0      0      1      1      1      1      0      1      0      0

CW26     1       1     0      1      0      1      1      0      0      1      0      0      0      1      1      0

CW27     1       1     0      1      1      1      0      0      0      0      1      0      1      0      0      1

CW28     1       1     1      0      0      0      0      1      0      1      0      0      1      1      0      1

CW29     1       1     1      0      1      0      1      1      0      0      1      0      0      0      1      0

CW30     1       1     1      1      0      1      0      1      1      0      0      1      0      0      0      0

CW31     1       1     1      1      1      1      1      1      1      1      1      1      1      1      1      1



eBCH-16 Codeword Selection and Bit Sequence Adjustment

The eBCH-16 codewords used for the AMCTL SHALL comply with the symbol DC balance principle
under both NRZ and PAM4 modulation. That is, the number of 0s or 1s (NRZ) or negative levels and
positive levels (PAM4) are equivalent in each symbol. Gray coding SHALL be required for PAM4
modulation.

Eight codewords that meet the DC balance requirements can be selected from Table 3-5. The number
of 0s and 1s in the upper eight bits and lower eight bits of each codeword is the same. eBCH (16,5)
codewords naturally meet DC balance requirements in NRZ modulation.

eBCH (16,5) codewords are adjusted as follows to meet DC balance requirements in both NRZ and
PAM4 modulation:

    Byte_A_new[7] = Byte_A_orig[4]
    Byte_A_new[6] = Byte_A_orig[3]
    Byte_A_new[5] = Byte_A_orig[2]




unifiedbus.com                                                                                                        29
3 Physical Layer



     Byte_A_new[4] = Byte_A_orig[7]
     Byte_A_new[3] = Byte_A_orig[5]
     Byte_A_new[2] = Byte_A_orig[1]
     Byte_A_new[1] = Byte_A_orig[6]
     Byte_A_new[0] = Byte_A_orig[0]
     Byte_B_new[7] = Byte_B_orig[7]
     Byte_B_new[6] = Byte_B_orig[5]
     Byte_B_new[5] = Byte_B_orig[4]
     Byte_B_new[4] = Byte_B_orig[3]
     Byte_B_new[3] = Byte_B_orig[2]
     Byte_B_new[2] = Byte_B_orig[1]
     Byte_B_new[1] = Byte_B_orig[6]
     Byte_B_new[0] = Byte_B_orig[0]

The following table lists the eight eBCH-16 codewords used for the AMCTL and their bit sequence
adjustment.

                              Table 3-6 Bit sequence adjustment for eBCH-16
                       Original BCH Code             NRZ                           PAM4
            eBCH
 No.                                                 Orig: (43275160_75432160)     Symbol #
            Code       (76543210_76543210)
                                                     New: (76543210_76543210)      (3210_3210)

 0          CW8        01000111_10101100             00100111_11011000             0312_2130
 1          CW28       11100001_01001101             00011011_00011011             0132_0132
 2          CW3        00011110_10110010             11100100_11100100             2310_2310
 3          CW23       10111000_01010011             11011000_00100111             2130_0312
 4          CW9        01001101_11000011             01100011_10000111             1302_3012
 5          CW21       10101100_10001110             01111000_10011100             1230_3120
 6          CW10       01010011_01110001             10000111_01100011             3012_1302
 7          CW22       10110010_00111100             10011100_01111000             3120_1230


eBCH-16 Error Correction Capability

eBCH(16,5) combines 1-bit even parity with BCH(15,5). It corrects up to 3-bit errors and sometimes
fixes 4-bit errors. There are four distributions of correctable errors:

       1.    1-bit error in a random position of the 16-bit eBCH codeword.
       2.    2-bit error in a random position of the 16-bit eBCH codeword.
       3.    3-bit error in a random position of the 16-bit eBCH codeword.




unifiedbus.com                                                                                       30
3 Physical Layer



      4.   3-bit error in a random position of the first 15-bit BCH codeword and 1-bit parity error.




                                Figure 3-8 All eBCH-16 correctable errors


3.2.4.2 AMCTL Structure

One AMCTL is 40-symbol long and consists of BODY, END, LID, CTRL_TYPE, and CTRL_DETAIL.

      ⚫    BODY, 12-symbol long, is the start field of the AMCTL and consists of three groups of the
           same eBCH-16 codewords (CW21 and CW28). BODY assists in identifying streams during
           AMCTL locking.
      ⚫    END, 4-symbol long, consists of two eBCH-16 codewords (CW22). It is used to identify the
           AMCTL during its locking process.
      ⚫    LID occupies eight symbols, structured as two identical 4-symbol groups. Each group of 4
           symbols consists of two eBCH-16 codewords. It is used to identify the current lane ID.
      ⚫    CTRL_TYPE occupies eight symbols, structured as two identical 4-symbol groups. Each
           group of 4 symbols consists of two eBCH-16 codewords. It carries control commands that
           have different codes. If no control command is delivered, CTRL_TYPE SHALL be set to No
           Command. After the RX identifies No Command, the content of CTRL_DETAIL SHALL be
           ignored.
      ⚫    CTRL_DETAIL occupies eight symbols, structured as two identical 4-symbol groups. Each
           group of 4 symbols consists of two eBCH-16 codewords. It is used to further classify each
           CTRL_TYPE command.
                                     Table 3-7 AMCTL field structure
 Symbol Number           Description
 0–11                    BODY: CW21, CW28
 12–15                   END: CW22, CW22
 16–23                   LID: Lane ID Indicator
 24–31                   CTRL_TYPE: Control Command Type




unifiedbus.com                                                                                         31
3 Physical Layer



 Symbol Number            Description
 32–39                    CTRL_DETAIL: Control Command Detail


AMCTL.LID

It specifies lane IDs that are used for scrambling seed identifying and lane reordering.

                                      Table 3-8 AMCTL.LID codewords
 Lane ID Indicator        LID [63:48]        LID [47:32]          LID [31:16]          LID [15:0]
 Lane0                    CW3                CW3                  CW3                  CW3
 Lane1                    CW3                CW8                  CW3                  CW8
 Lane2                    CW3                CW9                  CW3                  CW9
 Lane3                    CW3                CW10                 CW3                  CW10
 Lane4                    CW3                CW21                 CW3                  CW21
 Lane5                    CW3                CW22                 CW3                  CW22
 Lane6                    CW3                CW23                 CW3                  CW23
 Lane7                    CW3                CW28                 CW3                  CW28
 NULL                     CW21               CW3                  CW21                 CW3


AMCTL Controlling

AMCTL.CTRL_TYPE defines various control functions, and AMCTL.CTRL_DETAIL defines the sub-
functions of each control function.

AMCTL control functions:

      ⚫    FEC Control
           Specifies whether to enable or disable FEC for the subsequent data streams of the AMCTL.
      ⚫    Link Width Switch Indicator
           −   X0: EDF in Link_Active state. That is, after the AMCTL with EDF is sent, the link
               switches from sending flits to sending LTBs.
           −   x1, x2, x4, x8:
               ▪ TX switching width during dynamic link width switching in the Link_Active state.
               ▪ SDF in the Send_NullBlock state. That is, after AMCTL with SDF is sent, the link
                   switches from sending LTBs to sending flits.
      ⚫    EI Indicator
           This indicator is used when TX enters the electrical idle state.
           In the electrical idle state (for example, in the speed switching scenario), EI Indicator is used
           to indicate that the current lane enters the electrical idle state after sending the AMCTL.




unifiedbus.com                                                                                            32
3 Physical Layer



          The UB port sends the AMCTL with enter electrical idle (AMCTL with EEI) to notify the peer
          port that its TX will enter the electrical idle state after sending the AMCTL with EEI.
      ⚫   AMCTL Insert Period Control
          This specification supports different AMCTL insertion periods. In addition to the normal
          AMCTL insertion period (referred to as "Period0", configured by a vendor-defined register),
          this specification defines the short AMCTL insertion period (referred to as "Period1") used
          during the lane increasing process of quickly dynamic link width switch (QDLWS). When
          AMCTL.CTRL_TYPE == AMCTL Insert Period Control and AMCTL.CTRL_DETAIL ==
          Period1, the AMCTL insertion period of the subsequent stream is a short period, which is
          configured by using a vendor-defined register.
      ⚫   Remote TX Link Width Switch Indicator
          This control mode is used to forcibly request the peer end to quickly decrease lanes in the
          TX direction in Link_Active state. The lane decreasing process does not go through the
          Retrain state. For details, see Section 3.4.2.4.

                           Table 3-9 AMCTL.CTRL_TYPE codeword mapping
 CTRL_TYPE[63:48]/       CTRL_TYPE[47:32]/
                                                      Function
 CTRL_TYPE[31:16]        CTRL_TYPE[15:0]
 CW3                     CW8                          FEC Control
 CW8                     CW9                          Link Width Switch Indicator
 CW9                     CW10                         EI Indicator
 CW10                    CW21                         AMCTL Insert Period Control
 CW21                    CW22                         Remote TX Link Width Switch Indicator
 CW22                    CW23                         Reserved
 CW23                    CW28                         Reserved
 CW28                    CW3                          No Command


                         Table 3-10 AMCTL.CTRL_DETAIL codeword mapping
                         CTRL_DETAIL[63:48] /         CTRL_DETAIL[47:32] /
 CTRL_TYPE                                                                         Category
                         CTRL_ DETAIL [31:16]         CTRL_ DETAIL [15:0]
 FEC Control             CW3                          CW9                          Reserved
                         CW8                          CW10                         Reserved
                         CW9                          CW21                         Reserved
                         CW10                         CW22                         Reserved
                         CW21                         CW23                         Reserved
                         CW22                         CW28                         Reserved
                         CW23                         CW3                          Dynamic Close FEC
                         CW28                         CW8                          Dynamic Open FEC


 Link Width Switch       CW3                          CW9                          X0 (End of Data Flit)




unifiedbus.com                                                                                             33
3 Physical Layer



                       CTRL_DETAIL[63:48] /   CTRL_DETAIL[47:32] /
 CTRL_TYPE                                                           Category
                       CTRL_ DETAIL [31:16]   CTRL_ DETAIL [15:0]
 Indicator             CW8                    CW10                   x1
                       CW9                    CW21                   x2
                       CW10                   CW22                   x4
                       CW21                   CW23                   x8
                       CW22                   CW28                   Reserved
                       CW23                   CW3                    Reserved
                       CW28                   CW8                    Reserved


 EI Indicator          CW3                    CW9                    Reserved
                       CW8                    CW10                   Reserved
                       CW9                    CW21                   Reserved
                       CW10                   CW22                   Reserved
                       CW21                   CW23                   Reserved
                       CW22                   CW28                   Enter Electrical Idle
                                                                     (EEI)
                       CW23                   CW3                    Reserved
                       CW28                   CW8                    Reserved


 AMCTL Insert Period   CW3                    CW9                    Period0
 Control
                       CW8                    CW10                   Period1
                       CW9                    CW21                   Reserved
                       CW10                   CW22                   Reserved
                       CW21                   CW23                   Reserved
                       CW22                   CW28                   Reserved
                       CW23                   CW3                    Reserved
                       CW28                   CW8                    Reserved
 Remote TX Link        CW3                    CW9                    Reserved
 Width Switch
                       CW8                    CW10                   x1
 Indicator
                       CW9                    CW21                   x2
                       CW10                   CW22                   x4
                       CW21                   CW23                   x8
                       CW22                   CW28                   Reserved
                       CW23                   CW3                    Reserved
                       CW28                   CW8                    Reserved


 No Command            CW3                    CW9                    No Command




unifiedbus.com                                                                               34
3 Physical Layer



AMCTL Identification Mechanism

Because of fixed data length between two adjacent AMCTLs, the RX can periodically detect END. The
AMCTL is encoded using eBCH-16, and each codeword is capable of correcting errors.

If the received END matches the theoretical value after error correction, the RX considers that correct
AMCTL is received.

If the number of error bits of the received END exceeds the correction threshold of eBCH-16, the RX
considers that the AMCTL is not properly received and takes no further action. If the link is in the
Link_Active or Send_NullBlock state, the LMSM MAY enter the Retrain state to perform link training
and re-lock the AMCTL through slips. If the link is in other states, it re-locks the AMCTL through slips.
For details, see the AMCTL locking process.

LID[63:0] is divided into LID[63:32] and LID[31:0], which SHALL be identical. If the received AMCTL
contains different LID[63:32] and LID[31:0], the LID is invalid. After the AMCTL is locked, LIDs
corrected by eBCH-16 are recorded. If the LIDs corrected by eBCH-16 are the same after two
consecutive AMCTLs are received, the lane ID of the current lane is updated. Additionally, lane ID MAY
be determined by using the lane ID in LTB. The choice of method depends on the specific
implementation.

CTRL_TYPE[63:0] is divided into two identical parts: CTRL_TYPE[63:32] and CTRL_TYPE[31:0]. If
either CTRL_TYPE[63:32] or CTRL_TYPE[31:0] matches a valid codeword after eBCH-16 error
correction, the value is considered valid. If the two parts match valid codewords with different content,
the RX SHALL NOT perform the control operation.

Similarly, CTRL_DETAIL[63:0] is divided into two identical parts: CTRL_DETAIL[63:32] and
CTRL_DETAIL[31:0]. If either CTRL_DETAIL[63:32] or CTRL_DETAIL[31:0] matches a valid
codeword after eBCH-16 error correction, the value is considered valid. If the two parts match valid
codewords with different content, the RX SHALL NOT perform the control operation.


3.2.4.3 AMCTL Processing Rules on the TX

      ⚫    All lanes of a link on the TX SHALL operate at the same clock frequency.
      ⚫    The TX SHALL periodically insert the AMCTL with a length of 40 symbols on each lane.
      ⚫    AMCTL insertion rules when the LMSM is in the Send_NullBlock and Link_Active states:
           −   One AMCTL with SDF is sent first in the Send_NullBlock state, and then AMCTLs are
               periodically inserted.
           −   When the number of lanes is dynamically increased in the Link_Active state, the AMCTL
               insertion interval SHALL be negotiated and switched to Period1 before the RLTB is
               transmitted. The interval can be configured through a vendor-defined register, but the
               configured value SHALL ensure that a continuous LTB is not interrupted. By default, one
               AMCTL is inserted every 640 symbols. During the increase of the number of lanes, the
               AMCTL SHALL be inserted into lanes that transmit data and LTBs at the specified interval
               (Period1). After lanes increasing process is completed, the AMCTL insertion interval
               SHALL be switched back to pre-lane-increasing setting.



unifiedbus.com                                                                                              35
3 Physical Layer



      ⚫   In other LMSM states, one AMCTL SHALL be sent every 32 LTBs.
      ⚫   The AMCTL SHALL be inserted at the LTB boundaries.
      ⚫   The AMCTL SHALL NOT be involved in FEC encoding.
      ⚫   The AMCTL SHALL NOT be subject to scrambling and precoding.


3.2.4.4 AMCTL Processing Rules on the RX

      ⚫   The RX detects and locks the AMCTL according to the insertion rules on the TX.
      ⚫   The RX SHALL identify the AMCTL boundary by detecting END.
      ⚫   The RX uses a counter to track the number of bit streams between two consecutive
          AMCTLs. If the AMCTL insertion interval is 640 symbols, each of which contains eight bits,
          the data length between two adjacent AMCTLs is 5120 bits. The counter operates within a
          range of [0: 5120], starting at zero and stopping once it hits 5120. The RX clears the counter
          to zero upon detecting END and starts counting again after the next 24 symbols.

Implementation reference: AMCTL locking process

The AMCTL is periodically sent on each lane during link training and normal operations. The AMCTL
needs to be always locked on RX in normal situations.

The AMCTL locking SHALL be performed on each lane. The following figure shows the process.




                                  Figure 3-9 AMCTL locking process



unifiedbus.com                                                                                         36
3 Physical Layer



States involved in the AMCTL locking process:

      ⚫   Lock_Init
          Initial state before AMCTL detection. In this state, all variables are False by default. When
          link training starts, for example, in the Discovery state, the variable AMCTL_Lock_EN is set
          to True, and the next state is AMCTL_Slip.
      ⚫   AMCTL_Slip
          In this state, all variables except AMCTL_Lock_EN are reset to False. After a valid AMCTL
          is found in the received streams by searching for END via slip operations, the AMCTL_Valid
          variable is set to True and the next state is AMCTL_Align.
          In this state, the AMCTL is considered valid if END is correct, and BODY before END MAY
          be used as a reference.
      ⚫   AMCTL_Align
          This state is a temporary state, indicating that the first AMCTL identifier is recognized. After
          performing the required slip operations, the variable Slip_Done is set to True. After 24
          symbols following END, the variable AMCTL_CNT_Start is set to True, triggering the
          counter to begin checking whether the AMCTL reappears at the expected interval. During link
          training, the AMCTL interval is 32 LTBs (512 symbols, 4,096 bits). The counter stops when
          the count reaches 4,096, and the next state is AMCTL_Confirm.
      ⚫   AMCTL_Confirm
          In this state, the variable AMCTL_CNT_Done is True, checking whether a valid AMCTL is
          received.
          −   If several (configurable) valid AMCTLs are received, the next state is AMCTL_Lock, and
              AMCTLs are locked.
          −   If no valid AMCTL is received, the next state is AMCTL_Slip.
      ⚫   AMCTL_Lock
          This state is the locking state, which is a temporary state. After the variable AMCTL_Lock is
          set to True, the next state is AMCTL_Lock_Count.
      ⚫   AMCTL_Lock_Count
          In this state, AMCTL is periodically validated at the expected position on each lane.
          −   In the link training state, the interval is 512 symbols. To check if the AMCTL is valid, a
              correct END is required, while BODY serves as extra support for this decision. If BODY is
              wrong, only an error is logged, which does not change the AMCTL locking state.
          −   In the Send_NullBlock or Link_Active state, the AMCTL is checked whether it is at the
              expected position based on the interval. If no valid END is received, the received AMCTL
              is considered invalid.
          −   A new counting period is started once the current AMCTL finishes. The AMCTL is
              considered valid if it arrives at its anticipated position.




unifiedbus.com                                                                                             37
3 Physical Layer



            −   If no consecutive, valid AMCTL (the number is configurable) is received at anticipated
                positions:
                ▪ If the current state is Link_Active or Send_NullBlock, jump to the Retrain state of
                    the LMSM.
                ▪ If the current state is another state, jump to the AMCTL_Slip state as illustrated in the
                    AMCTL locking process.


3.2.5 Symbol Distribution and Bit Sequence

3.2.5.1 Symbol Transmission Sequence on a Lane

NRZ

In NRZ mode, every symbol contains eight bits (from bit 7 to bit 0). Bit 0 is the LSB, and bit 7 is the MSB.
Each symbol (including data, link management block (LMB), and AMCTL) is sent to a lane in the
sequence of bit 0, bit 1,..., bit 7.

The following figure shows the bit sequence of symbols transmitted on a lane in NRZ mode.




                    Figure 3-10 Bit sequence of symbols transmitted on a lane in NRZ mode

Note: In NRZ mode, each UI contains one bit.

PAM4

In PAM4 mode, each symbol (including data, LMB, and AMCTL) contains eight bits (from bit 7 to bit 0).
Bit 0 is the LSB.

The following figure shows the bit sequence of symbols transmitted on a lane in PAM4 mode.




unifiedbus.com                                                                                             38
3 Physical Layer




                   Figure 3-11 Bit sequence of symbols transmitted on a lane in PAM4 mode

Note: In PAM4 mode, each UI contains two bits.


3.2.5.2 AMCTL Transmission Sequence

One AMCTL in the TX direction consists of 40 symbols, each of which has 8 bits.

The transmission sequence of symbols is symbol0, symbol1, symbol2,..., symbol39.

Bit 0 is transmitted first, followed by bit 1, bit 2,..., and bit 7 in each symbol.

For example, symbols 0 to 3 are AMCTL.BODY, and the mapping is as follows:




                       Figure 3-12 Bit sequence for AMCTL transmission in NRZ mode




unifiedbus.com                                                                              39
3 Physical Layer




                      Figure 3-13 Bit sequence for AMCTL transmission in PAM4 mode


3.2.5.3 LMB Transmission Sequence

Each LMB, including LTB and EEIB, has 16 symbols (see Section 3.4.1). Symbol 0 is transmitted first,
followed by symbol 1 to symbol 15.

Each symbol has eight bits. Bit 0 is transmitted first, followed by bit 1, bit 2,..., and bit 7.




                          Figure 3-14 LMB bit transmission sequence in NRZ mode

For details about the LMB bit transmission sequence on a lane in PAM4 mode, see Figure 3-11.




unifiedbus.com                                                                                     40
3 Physical Layer



3.2.5.4 Symbol Distribution in FEC Bypass Mode

Flits are transmitted on links in Send_NullBlock and Link_Active states. A packet at the data link layer
MAY consist of several flits, each of which has 20 symbols. Null Blocks (see Section 4.3.3.2) are
transmitted on links when there are no traffic at the upper layer or traffic cannot fully occupy the link
bandwidth. The AMCTL is periodically inserted into each lane for physical-layer frame alignment.

In FEC bypass mode, the length of each symbol is 1 byte. In the Send_NullBlock state, Null Blocks
are transmitted following a AMCTL with SDF, which is sequentially transmitted to each lane with symbol
granularity in a round-robin manner starting from Lane 0. All later packets follow in order.

Unless the link training state transition is required, only the AMCTL can be interleaved between data.

For details about the bit transmission sequence of each symbol on a lane, see Section 3.2.5.1.

Figure 3-16 shows how data is distributed across an x8 link in FEC Bypass mode using a 640-symbol
interval between AMCTLs. Each AMCTL in the figure has a complete structure.

Assume that there are three data link layer packets, each packet includes multiple symbols, and each
symbol is expressed by Packet No., Flit No., and Symbol No. For example, P0.F1.S2 represents
Symbol 2 in Flit 1 of Packet 0. The first symbol sent by Packet0 on the link is P0.F0.S0, that is, Byte0 of
the link packet header (LPH). For details, see Section 4.3.2.2.2.




                   Figure 3-15 Symbol representation of the first flit in a data link layer packet

Each Null Block includes one flit, and the symbol of the Null Block is expressed as NB.Sx.

The figure shows three data link layer packets (Packet0, Packet1, and Packet2) and several Null Blocks.

      1.   Packet0 consists of two flits, with a total of 40 symbols transmitted on a link in sequence,
           expressed as P0.F0.S0, P0.F0.S1 ... P0.F0.S19, P0.F1.S0, P0.F1.S1 ... P0.F1.S19.
      2.   Packet1 consists of two flits, with a total of 40 symbols transmitted on a link in sequence,
           expressed as P1.F0.S0, P1.F0.S1 ... P1.F0.S19, P1.F1.S0, P1.F1.S1 ... P1.F1.S19.
      3.   Packet2 consists of one flit, with a total of 20 symbols transmitted on a link in sequence,
           expressed as P2.F0.S0, P2.F0.S1 ... P2.F0.S19.




unifiedbus.com                                                                                              41
3 Physical Layer




                      Figure 3-16 Data distribution and framing in FEC Bypass mode


3.2.5.5 Symbol Distribution in FEC Mode

Symbol Distribution in FEC Interleaved Mode

Data from the data link layer and Null Blocks are distributed to each FEC encoder starting from S0 at a
granularity of eight bits. After parity symbols p7 (most significant byte) to p0 are added to FEC encoders,
each encoder sends the FEC frame symbols to each lane in interleaved mode.

For details about the bit transmission sequence of each symbol on a lane, see Section 3.2.5.1.




                           Figure 3-17 Flit symbols in RS (128,120) FEC mode




unifiedbus.com                                                                                           42
3 Physical Layer



The following figure (x8 as an example) shows the symbol distributions. mA119 to mA0 and mB119 to mB0
are message symbols. pA7 to pA0 and pB7 to pB0 are FEC parity symbols.




           Figure 3-18 Symbol distribution in RS (128,120) FEC interleaved mode on an x8 link




unifiedbus.com                                                                                          43
3 Physical Layer



The following figure shows the framing of FEC symbols on lanes.




          Two
          FEC
        frames




          Two
          FEC
        frames




                 Figure 3-19 Data distribution and framing in RS (128,120) FEC interleaved mode




unifiedbus.com                                                                                    44
3 Physical Layer



Symbol Distribution in Non-interleaved FEC Mode

Distribution rules of the non-interleaved FEC mode:




                    Figure 3-20 Distribution in non-interleaved RS(128,120) FEC mode

mA119 to mA0 are message symbols, and pA7 to pA0 are FEC parity symbols.


3.2.6 Low-Power Mechanism on Datapaths
If there is no data to be sent in data link layer, PCS MAY send Null Blocks. These blocks undergo FEC
encoding and scrambling before being sent to the SerDes. This keeps the SerDes clock data recovery
(CDR) lock stable for the remote UBPU but increases the physical layer's dynamic power usage.

UB provides a control mechanism to reduce the dynamic power consumption in the physical layer.
Specifically, the PCS MAY stop inserting Null Blocks and disables FEC encoding and scrambling in
case of no data stream from data link layer. This feature is optional. The process is as follows:




unifiedbus.com                                                                                      45
3 Physical Layer



Procedure for Closing PCS:

      1.   After the PCS detects that no data is delivered from the data link layer, it finishes transmitting
           current data.
      2.   Send one AMCTL, with AMCTL.CTRL_TYPE set to FEC Control and
           AMCTL.CTRL_DETAIL set to Dynamic Closed FEC.
      3.   Send PRBS23 streams to each lane of the SerDes and disable the PCS TX scrambling and
           FEC logic after AMCTL transmission is completed. Sending PRBS23 streams keeps the
           SerDes CDR lock on the remote UBPU. The PRBS23 polynomial is the same as
           scrambling's. During PRBS23 stream transmission, AMCTLs are periodically inserted.
      4.   The peer RX receives and parses AMCTLs. If AMCTL.CTRL_TYPE == FEC Control and
           AMCTL.CTRL_DETAIL == Dynamic Closed FEC, the PCS turns off the RX descrambling
           and FEC logic once data processing finishes. The AMCTL locking circuit continuously
           monitors incoming data for AMCTL control commands that enable FEC and scrambling.

Procedure for Opening PCS:

      1.   After detecting that data is delivered from the data link layer, the PCS stops sending
           PRBS23 streams.
      2.   After PRBS23 streams are stopped, it sends one AMCTL per lane immediately, with
           AMCTL.CTRL_TYPE being FEC Control and AMCTL.CTRL_DETAIL being Dynamic
           Open FEC.
      3.   Receive data link layer data and enable FEC encoding and scrambling normally.
      4.   The peer RX receives and parses AMCTLs. If AMCTL.CTRL_TYPE == FEC Control and
           AMCTL.CTRL_DETAIL == Dynamic Open FEC, RX descrambling and FEC decoding are
           enabled, and data is received normally.


3.3 Physical Medium Attachment
The PMA receives parallel data from the PCS, completes serialization, Gray coding (for PAM4
modulation) and precoding, and sends the data to the TX lane. It receives serial streams from the RX
lane, performs CDR, Gray decoding (for PAM4 modulation), and pre-decoding, completes
deserialization, and delivers parallel data to the PCS.

The PMA offers drivers, pre-emphasis, and equalization capabilities for high-speed signaling, mitigating
transmission line high-frequency losses and reducing inter-symbol interference (ISI).

The PMA SHALL support CDR to recover clock signals from the received serial streams.

The PMA SHALL allow the PCS to connect to multiple physical medium links in a medium-independent
manner and supports lane configurations of x1, x2, x4, or x8 on either the port TX or RX. The TX and
RX within a port may consist of the same or different number of lanes.

The PMA SHALL work in PHY Mode-1 or PHY Mode-2. The working mode SHALL be configured before
power-on. For details about the supported data rates and modulation modes, see Section 3.1.2.




unifiedbus.com                                                                                            46
3 Physical Layer



PMA SHALL provide Gary coding with PAM4 modulation. Also, PMA SHALL provide precoding.


3.3.1 Gray Coding
PAM4 modulation requires sending Gray-coded data to the PMA in 2-bit units. Gray coding is performed
only on symbols that need to be scrambled.

A PAM4 signal has four levels (00, 01, 10, and 11, arranged from lowest to highest), each of which is
mapped to two bits.

Compared with NRZ modulation, PAM4 modulation has less tolerance between levels, leading to a
higher BER. Gray coding minimizes bit errors by ensuring that a misinterpretation of a signal level as an
adjacent level results in only a single-bit error.

                              Table 3-11 PAM4 modulation and level mapping
         Raw PAM4 Data                        Gray-coded Data             Level After Gray Coding
                   00                                00                                0
                   01                                01                                1
                   11                                10                                2
                   10                                11                                3




                                           Figure 3-21 PAM4 levels


3.3.2 Precoding
UB supports precoding to prevent burst errors. The TX precodes data on each channel and the RX
decodes data.




unifiedbus.com                                                                                          47
3 Physical Layer




                                      Figure 3-22 Precoding illustration

When NRZ modulation is used:

      ⚫   Tn=(Pn^Tn-1) applies in the TX direction. Pn is the input precoding data, Tn is the resulting
          output data, and Tn-1 is the output of the previous unit interval (UI) before precoding. If the
          data of the previous UI is not scrambled, Tn-1 SHALL be set to 1'b1.
      ⚫   P'n=(Rn^Rn-1) applies in the RX direction. Rn is the input precoding data, P'n is the
          resulting output data, and Rn-1 is the output of the previous UI before precoding. If the data
          of the previous UI is not scrambled, Rn-1 SHALL be set to 1'b1.

When PAM4 modulation is used:

      ⚫   Tn=(Pn-Tn-1)mod4 applies in the TX direction. Pn is the input precoding data, Tn is the
          resulting output data, and Tn-1 is the output of the previous UI before precoding. If the data
          of the previous UI is not scrambled, Tn-1 SHALL be set to 2'b00.
      ⚫   P'n=(Rn+Rn-1)mod4 applies in the RX direction. Rn is the input precoding data, P'n is the
          resulting output data, and Rn-1 is the output of the previous UI before precoding. If the data
          of the previous UI is not scrambled, Rn-1 SHALL be set to 2'b00.

Only scrambled bits are precoded.


3.4 Link State Management
The link management state machine (LMSM) manages the link training process, training links to a state
that can be used by the data link layer. When a link error occurs, the recovery process is performed to
enhance link resilience.


3.4.1 Link Management Block (LMB)
The physical layer SHALL generate link management blocks (LMBs) for training and state control. An
LMB consists of 16 symbols (8 bits each).

All active lanes of a link SHALL transmit identical LMBs simultaneously.

There are two LMB types:

      ⚫   Link training block (LTB)
      ⚫   Exit electrical idle block (EEIB)




unifiedbus.com                                                                                              48
3 Physical Layer



3.4.1.1 LTB

Both sides of a link exchange LTB s during link training.

This specification defines four LTB types:

      ⚫    Discovery LTB (DLTB)
      ⚫    Config LTB (CLTB)
      ⚫    Retrain LTB (RLTB)
      ⚫    Equalization LTB (ELTB)

If symbols 0 to 11 of an LTB are the same as those of its previous LTB and the CRC check passes, the
two LTBs are considered consecutive.

The requirements for reserved bits in an LTB are as follows:

      ⚫    The TX SHALL transmit 0s for reserved bits.
      ⚫    The RX SHALL ignore reserved bits for LTB validation.
      ⚫    The RX SHALL not take any functional control action by checking reserved bits.
      ⚫    LTB symbols 0 to 11 are used to calculate the CRC, and the CRC result SHALL be filled in
           symbol 12 (LTB CRC[7:0]) and symbol 13 (LTB CRC[15:8]). The CRC polynomial is as
           follows:

                         x^16 + x^14 + x^12 + x^11 + x^8 + x^5 + x^4 + x^2 + 1

LTB types are defined as follows:

DLTB: used to lock symbols, exchange link initialization information, and determine the TX/RX link
width in the Discovery state; and to lock symbols and perform RX equalization adaptation in the
RXEQ_Optimize state in fixed data rate mode.

CLTB: used to negotiate the equalization mode and FEC mode in the Config state.

RLTB: used to switch the data rate, adjust the link width, and recover the link from an error in the
Retrain state.

ELTB: used to negotiate link equalization in the Equalization state.

Tables 3-12 to 3-15 list the formats and fields of these LTBs.

                                       Table 3-12 DLTB definition
 Symbol Number        Description
 0                    Type
                          0xA0: Discovery.Active
                          0xA1: Discovery.Confirm
                          0xE0: RXEQ_Optimize
                          Others: reserved




unifiedbus.com                                                                                         49
3 Physical Layer



 Symbol Number     Description
 1                 Link_ID
                      Bits [7:0]: 0–254, NULL
                             The NULL value is 8'hFF.
 2                 Lane_ID
                       Bits [7:0]: 0–7, NULL
                             The NULL value is 8'hFF.
 3                 TX Link Width (TLW)
                       Bits [5:0]:
                             6'b00_0001: x1
                             6'b00_0010: x2
                             6'b00_0100: x4
                             6'b00_1000: x8
                             Others: reserved
                      Bits [7:6]: reserved
 4                 RX Link Width (RLW)
                       Bits [5:0]:
                             6'b00_0001: x1
                             6'b00_0010: x2
                             6'b00_0100: x4
                             6'b00_1000: x8
                             Others: reserved
                      Bits [7:6]: reserved
 5                 Data_Rate_Support_1
                      A bit set to 1'b1 indicates support for the corresponding data rate, while a bit
                      set to 1'b0 indicates no support for the corresponding data rate.
                      Bit 0: Data Rate 0 (PHY Mode-1: 4.0 Gbit/s; PHY Mode-2: 2.578125 Gbit/s)
                      Bit 1: Data Rate 1 (reserved)
                      Bit 2: Data Rate 2 (PHY Mode-2: 25.78125 Gbit/s)
                      Bit 3: Data Rate 3 (PHY Mode-1: custom data rate 1)
                      Bit 4: Data Rate 4 (PHY Mode-2: 53.125 Gbit/s)
                      Bit 5: Data Rate 5 (PHY Mode-1: custom data rate 2)
                      Bit 6: Data Rate 6 (reserved)
                      Bit 7: Data Rate 7 (PHY Mode-1: custom data rate 3)
 6                 Data_Rate_Support_2
                      Bit 0: Data Rate 8 (PHY Mode-2: 106.25 Gbit/s)
                      Bits [7:1]: reserved
 7                 FEC_Mode_Support
                      Bit 0: RS (128, 120, T=2)
                             1'b0: This FEC mode is not supported.
                             1'b1: This FEC mode is supported.




unifiedbus.com                                                                                       50
3 Physical Layer



 Symbol Number     Description
                       Bit 1: RS (128, 120, T=4)
                            1'b0: This FEC mode is not supported.
                            1'b1: This FEC mode is supported.
                       Bits [7:2]: reserved
 8                 Bit 0: Port_Type
                       1'b0: secondary port
                       1'b1: primary port
                   Bits [7:1]: PortNego_Random_Value
                       1–127, NULL
                       The NULL value is 0.
 9                 Reserved
 10                FEC_Interleave_Support
                       A bit set to 1'b1 indicates support for FEC interleave in the link width, while a
                       bit set to 1'b0 indicates no support for FEC interleave.
                       Bit 0: x1
                       Bit 1: x2
                       Bit 2: x4
                       Bit 3: x8
                       Bits [7:4]: reserved
 11                Bits [2:0]: RX_Lane0_ID
                       Position of logic RX lane 0 on the link:
                       3'b000: Logic RX lane 0 is on physical lane 0.
                       3'b001: Logic RX lane 0 is on physical lane 1.
                       3'b011: Logic RX lane 0 is on physical lane 3.
                       3'b100: Logic RX lane 0 is on physical lane 7.
                       Others: reserved
                   Bits [5:3]: MAX_LINK_WIDTH
                       Maximum link width:
                       3'b000: x1
                       3'b001: x2
                       3'b010: x4
                       3'b011: x8
                       Others: reserved
                   Bits [7:6]: reserved
 12                Bits [7:0]: CRCL
                       CRC[7:0] of DLTB symbols 0 to 11
 13                Bits [7:0]: CRCH
                       CRC[15:8] of DLTB symbols 0 to 11
 14                0x5A padding
 15                0x5A padding




unifiedbus.com                                                                                         51
3 Physical Layer



                                     Table 3-13 CLTB definition
 Symbol Number     Description
 0                 Type
                      0xB0: Config.Active
                      0xB1: Config.Check
                      0xB2: Config.Confirm
                      Others: reserved
 1                 Link_ID
                      Bits [7:0]: 0–254, NULL
                             The NULL value is 8'hFF.
 2                 Lane_ID
                       Bits [7:0]: 0–7, NULL
                             The NULL value is 8'hFF.
 3                 TX Link Width (TLW)
                       Bits [5:0]:
                             6'b00_0001: x1
                             6'b00_0010: x2
                             6'b00_0100: x4
                             6'b00_1000: x8
                             Others: reserved
                       Bits [7:6]: reserved
 4                 RX Link Width (RLW)
                       Bits [5:0]:
                             6'b00_0001: x1
                             6'b00_0010: x2
                             6'b00_0100: x4
                             6'b00_1000: x8
                             Others: reserved
                       Bits [7:6]: reserved
 5                 Reserved
 6                 EQ_Mode_Ctrl
                   Bits [1:0]: EQ_Mode
                      2'b00: Full_EQ
                      2'b01: Only_Highest_Data_Rate_EQ
                      2'b10: Skip_EQ
                      2'b11: Reserved
                      When LinkUp == 0 and the supported data rate is Data Rate 1 or higher,
                      this field is used for negotiating the equalization mode in the Config state.
                   Bits [4:2]: FEC_Mode_Ctrl
                      3'b000: FEC bypass
                      3'b001: RS (128, 120, T=2)




unifiedbus.com                                                                                        52
3 Physical Layer



 Symbol Number     Description
                       3'b010: RS (128, 120, T=4)
                       Others: reserved
                   Bit 5: FEC_Interleave_Ctrl
                       1'b1: Enable FEC interleave.
                       1'b0: Disable FEC interleave.
                   Bits [7:6]: reserved
 7                 Bits [7:0]: reserved
 8                 Bits [7:0]: reserved
 9                 Bits [7:0]: reserved
 10                Bits [7:0]: reserved
 11                Bits [7:0]: reserved
 12                Bits [7:0]: CRCL
                       CRC[7:0] of CLTB symbols 0 to 11
 13                Bits [7:0]: CRCH
                       CRC[15:8] of CLTB symbols 0 to 11
 14                0x5A padding
 15                0x5A padding


                                    Table 3-14 RLTB definition
 Symbol Number     Description
 0                 Type
                       0xC0: Retrain.Active
                       0xC1: Retrain.Confirm
                       0xC2: Retrain.LP1_PHY_Up
                       0xC3: Retrain.EQ_Initial
                       Others: reserved
 1                 Bits [7:0]: reserved
 2                 EQ_Ctrl1
                   Bits [5:0]:
                       When RLTB.Type == Retrain.EQ_Initial, this field is:
                           Local_HS: Local_HS value for the next data rate in the Retrain.Confirm
                           state.
                       Otherwise, this field is:
                           Post-Cursor: post-cursor coefficient at the current data rate.
                   Bits [7:6]: reserved




unifiedbus.com                                                                                  53
3 Physical Layer



 Symbol Number     Description
 3                 EQ_Ctrl2
                      When RLTB.Type == Retrain.EQ_Initial:
                          Bits [5:0]: Local_LS
                              Local_LS value for the next data rate transmitted in the
                              Retrain.Confirm state.
                           Bits [7:6]: reserved
                      Otherwise:
                           If the modulation mode at the current data rate is NRZ:
                              Bits [5:0]: Pre-Cursor: pre-cursor coefficient at the current data rate.
                              Bits [7:6]: reserved
                           If the modulation mode at the current data rate is PAM4:
                              Bits [3:0]: Second_Pre-Cursor: second pre-cursor coefficient at
                              the current data rate.
                              Bits [7:4]: Third_Pre-Cursor: third pre-cursor coefficient at the
                              current data rate.
 4                 EQ_Ctrl3
                      When RLTB.Type == Retrain.EQ_Initial:
                           Bits [3:0]: Remote_Initial_TX_Preset
                           Bits [7:4]: reserved
                      Otherwise:
                           Bits [7:0]: Cursor: cursor coefficient at the current data rate.
 5                 Data_Rate_Support_1
                       A bit set to 1'b1 indicates support for the corresponding data rate, while a
                       bit set to 1'b0 indicates no support for the corresponding data rate.
                       Bit 0: Data Rate 0 (PHY Mode-1: 4.0 Gbit/s; PHY Mode-2: 2.578125 Gbit/s)
                       Bit 1: Data Rate 1 (reserved)
                       Bit 2: Data Rate 2 (PHY Mode-2: 25.78125 Gbit/s)
                       Bit 3: Data Rate 3 (PHY Mode-1: custom data rate 1)
                       Bit 4: Data Rate 4 (PHY Mode-2: 53.125 Gbit/s)
                       Bit 5: Data Rate 5 (PHY Mode-1: custom data rate 2)
                       Bit 6: Data Rate 6 (reserved)
                       Bit 7: Data Rate 7 (PHY Mode-1: custom data rate 3)
 6                 Data_Rate_Support_2
                       Bit 0: Data Rate 8 Supported (PHY Mode-2: 106.25 Gbit/s)
                       Bits [6:1]: reserved
                       Bit 7: Change_Speed: valid when data rate change is enabled. The value
                       is 1'b1.
 7                 Bits [2:0]: FEC_Mode_Ctrl
                       3'b000: FEC bypass
                       3'b001: RS (128, 120, T=2)
                       3'b010: RS (128, 120, T=4)




unifiedbus.com                                                                                        54
3 Physical Layer



 Symbol Number     Description
                        Others: reserved
                   Bit 3: FEC/CRC_Mode_Reject
                        1'b0: Accept.
                        1'b1: Reject.
                   Bits [5:4]: Pre-FEC_BER_Measurement_Status
                        2'b00: BER is not measured, or the FEC mode configured by software is
                        used.
                        2'b01: BER measurement starts.
                        2'b10: BER measurement is completed.
                        2'b11: reserved
                   Bit 6: FEC_Interleave_Enable
                        1'b0: Disable FEC interleave.
                        1'b1: Enable FEC interleave.
                   Bit 7: FEC_Interleave_Ctrl_Reject
                        1'b0: Accept.
                        1'b1: Reject.
 8                 Bits [7:0]: reserved
 9                 Link_Ctrl
                   Bits [6:0]: reserved
                   Bit 7: Request_Equalization
                        1'b0: no equalization request
                        1'b1: equalization request
 10                Bits [2:0]: CRC_Mode_Ctrl
                        3'b000: no CRC
                        3'b001: CRC30
                        Others: reserved
                   Bit [3]: reserved
                   Bits [7:4]: Local_TX_Preset
                        Local TX preset value at the current data rate.
 11                If the modulation mode at the current data rate is PAM4:
                        Bits [5:0]: First_Pre-Cursor: first pre-cursor coefficient at the current data
                        rate.
                        Bits [7:6]: reserved
                   Otherwise:
                        Bits [7:0]: reserved
 12                Bits [7:0]: CRCL
                        CRC[7:0] of RLTB symbols 0 to 11
 13                Bits [7:0]: CRCH
                        CRC[15:8] of RLTB symbols 0 to 11
 14                0x5A padding




unifiedbus.com                                                                                       55
3 Physical Layer



 Symbol Number     Description
 15                0x5A padding


                                     Table 3-15 ELTB definition
 Symbol Number     Description
 0                 Type
                        0xD0: equalization
                        Others: reserved
 1                 Bits [4:0]: reserved
                   Bit 5: EQ_Reject
                        1'b0: Accept.
                        1'b1: Reject.
                   Bits [7:6]: reserved
 2                 EQ_Ctrl1
                   Bits [1:0]: Current_EQ_Phase
                        2'b00: Coarsetune_Active
                        2'b01: Coarsetune_Confirm
                        2'b10: EQ.Active (secondary port) or EQ.Passive (primary port)
                        2'b11: EQ.Passive (secondary port) or EQ.Active (primary port)
                   Bit 2: reserved
                   Bit 3: Preset_Mode_En
                        1'b0: Do not use the preset mode.
                        1'b1: Use the preset mode.
                   Bits [7:4]: TX_Preset
 3                 EQ_Ctrl2
                   These bits are valid only when Preset_Mode_En == 0.
                   If the modulation mode at the current data rate is NRZ:
                        Bits [5:0]: Pre-Cursor: pre-cursor coefficient at the current data rate.
                        Bits [7:6]: reserved
                   If the modulation mode at the current data rate is PAM4:
                        Bits [3:0]: Second_Pre-Cursor: second pre-cursor coefficient at the
                        current data rate.
                        Bits [7:4]: Third_Pre-Cursor: third pre-cursor coefficient at the current
                        data rate.
 4                 EQ_Ctrl3
                   These bits are valid only when Preset_Mode_En == 0.
                   Bits [5:0]: Post-Cursor: post-cursor coefficient at the current data rate.
                   Bits [7:6]: reserved
 5                 EQ_Ctrl4
                   These bits are valid only when Preset_Mode_En == 0.
                   Bits [7:0]: Cursor: cursor coefficient at the current data rate.




unifiedbus.com                                                                                      56
3 Physical Layer



 Symbol Number          Description
 6                      If the modulation mode at the current data rate is PAM4:
                               Bits [5:0]: First_Pre-Cursor: first pre-cursor coefficient at the current data
                               rate.
                               Bits [7:6]: reserved
                        Otherwise:
                               Bits [7:0]: reserved
 7-11                   Reserved
 12                     Bits [7:0]: CRCL
                               CRC[7:0] of ELTB symbols 0 to 11
 13                     Bits [7:0]: CRCH
                               CRC[15:8] of ELTB symbols 0 to 11
 14                     0x5A padding
 15                     0x5A padding


3.4.1.2 EEIB

An EEIB is a low frequency pattern designed to ensure that the RX's electrical idle exit detection circuit
can detect the electrical idle exit signal and exit the electrical idle state.

An EEIB sequence contains different numbers of EEIBs at different data rates.

When the data rate is less than or equal to 4.0 Gbit/s, one EEIB exists.

When the data rate is 25.78125 Gbit/s, two EEIBs exist.

When the data rate is 53.125 Gbit/s, four EEIBs exist.

When the data rate is 106.25 Gbit/s, eight EEIBs exist.

An EEIB sequence is formed only when EEIB are transmitted back to back without interruption.

                    Table 3-16 EEIB sequence at 2.578125 Gbit/s and 4.0 Gbit/s (NRZ)
 Symbol Number                        Value           Description
 0, 2, 4, 6, 8, 10, 12, 14            0x00            A low frequency pattern that alternates between eight
                                                      0s and eight 1s.
 1, 3, 5, 7, 9, 11, 13, 15            0xFF


                              Table 3-17 EEIB sequence at 25.78125 Gbit/s (NRZ)
 Symbol Number                        Value           Description
 0, 1, 2, 3, 8, 9, 10, 11             0x00            A low frequency pattern that alternates between thirty-
                                                      two 0s and thirty-two 1s.
 4, 5, 6, 7, 12, 13, 14, 15           0xFF




unifiedbus.com                                                                                                57
3 Physical Layer



                              Table 3-18 EEIB sequence at 53.125 Gbit/s (PAM4)
 Symbol Number                        Value         Description
 0, 1, 2, 3, 4, 5, 6, 7               0x00          Thirty-two Level 0 UIs
 8, 9, 10, 11, 12, 13, 14, 15         0xFF          Thirty-two Level 3 UIs


                              Table 3-19 EEIB sequence at 106.25 Gbit/s (PAM4)
 Symbol Number                         Value       Description
 0–15                                  0x00        Sixty-four Level 0 UIs
 16–31                                 0xFF        Sixty-four Level 3 UIs

Note: EEIB sequences at custom data rates are defined by vendors.



3.4.2 Link State Management Features
Link state management supports the following features:

      ⚫     Both electrical and optical links
      ⚫     FEC mode negotiation and dynamic FEC mode switching
      ⚫     Link width negotiation and dynamic link width switching
      ⚫     Quick link width degradation on error condition
      ⚫     Data rate negotiation and rate change
      ⚫     Lane reversal
      ⚫     Lane polarity detection and inversion
      ⚫     Equalization negotiation


3.4.2.1 Port Type Negotiation

Each UB link SHALL designate one port as primary and the other as secondary. They paly different
roles during link training.

Port type negotiation SHALL occur during the Discovery.Active substate if enabled via the Port Type
Negotiation Enable bit in the PHY Link Control register. If disabled, both ports SHALL be pre-configured
with fixed roles prior to link training.

      1.    Each port SHALL generate a 7-bit random number using an implementation-specific random
            number generator.
      2.    The port SHALL set:
            ▪    DLTB.Port_Type (symbol 8, bit 0) = "0" (initially secondary)
            ▪    DLTB.PortNego_Random_Value (symbol 8, bits [7:1]) = random value
      3.    Upon receiving a DLTB:
            ▪    If the received PortNego_Random_Value differs from the previously received value,
                 compare the 7-bit values.



unifiedbus.com                                                                                        58
3 Physical Layer



                 -   The port with the larger value SHALL become primary (Port_Type = 1).
                 -   The port with the smaller value SHALL remain secondary (Port_Type = 0).
           ▪     If the received value matches the previously received one and equals the local
                 transmitted value, generate a new 7-bit random number and retransmit.
      4.   Negotiation SHALL complete when both ports observe consistent Port_Type values in 8
           consecutive DLTBs on all active lanes.




                                      Figure 3-23 Port type negotiation

If the random number received by one end in the DLTB is identical to the one it previously transmitted, a
new random number is generated and transmitted. Subsequently, comparisons only occur when the
random number received in the DLTB differs from the previously received one.

When port type negotiation is disabled, the primary and secondary roles SHALL be statically assigned
via configuration registers before entering Link_Idle.


3.4.2.2 Link Width Negotiation

A UB link comprises one or more lanes, with the number of lanes being the link width. Each direction
(TX or RX) SHALL support standard widths of x1, x2, x4, or x8 lanes.

UB supports symmetric links, meaning a port has an equal number of TX and RX lanes. Before link
training starts, the number of lanes supported by the ports at both ends of a link may differ. After
entering the Discovery state, the negotiated maximum link width is used to form symmetric links.

UB also supports asymmetric links, where each port can support different numbers of TX and RX lanes.
The link width in each direction of an asymmetric link SHALL be a standard link width. For example,
port A has a TX link width of x8 and an RX link width of x4, while port B has a TX link width of x4 and an
RX link width of x8. After link training, the link width will be x8 from port A to port B and x4 from port B to
port A.




unifiedbus.com                                                                                               59
3 Physical Layer



3.4.2.3 Quickly Dynamic Link Width Switch (QDLWS)

The link width can be changed through the LMSM. The state transition is as follows:

Link_Active->Retrain->Discovery->Config->Send_NullBlock->Link_Active

In this approach, a link transitions to the training state, which interrupts service data. It typically
happens when the link width needs to be renegotiated due to a link error condition.

UB supports QDLWS to switch the link width without interrupting service data.

When QDLWS is enabled, the primary port can request to increase or decrease the number of lanes for
link width switch, and the secondary port can accept or reject the switch request.

QDLWS SHALL comply with the following rules:

      ⚫    The link SHALL first complete equalization negotiation for an appropriate data rate at the
           maximum link width and trains to the Link_Active state.
      ⚫    A new link width adjustment request SHALL be sent at least 1 μs after the previous
           adjustment request is completed.
      ⚫    The requested link width SHALL be the standard link width.
      ⚫    A port can request to adjust the TX or RX width independently, or request to adjust both TX
           and RX widths.
      ⚫    A port that receives a QDLWS request and is not ready SHALL respond with NAK to reject
           the request.

The QDLWS process is as follows:

Example 1: Link width degradation from TX4RX2 to TX2RX2




                              Figure 3-24 QDLWS link width decrease process



unifiedbus.com                                                                                            60
3 Physical Layer



Port A initiates a link width decrease request to switch its TX width from x4 to x2.

1.A: Port A's data link layer transmits a DLLCP LM block (see Section 4.3.3.7) to port B to reduce the
TX width to x2. The LM block carries Byte0.Bit0 = 1'b1 (Change TLW request) and Byte2.Bits[5:0] =
6'b000010 (TX link width = x2).

2.B: Port B's data link layer receives the LM block from port A, parses each field, and determines that
link width decrease is allowed. Then, port B transmits an LM block to port A to accept the link width
decrease request. The LM block carries Byte1.Bit0 = 1'b1 (Change TLW request RSP = ACK) and
Byte3.Bits[5:0] = 6'b000010 (RX link width = x2).

If port B is not ready or does not allow the link width decrease request from port A, it SHALL transmit an
LM block to port A to reject the link width decrease request. The LM block carries Byte1.Bit0 = 1'b0
(Change TLW request RSP = NAK) and Byte3.Bits[5:0] = 6'b000100 (RX Link Width = x4).

3.A: Port A's data link layer receives the LM block from port B, parses each field, and confirms that port
B has returned ACK.

If port A receives NAK from port B in the LM block, the process ends.

4.A: Port A's data link layer directs its physical layer to initiate the link width decrease process. The
physical layer transmits a control AMCTL (AMCTL.CTRL_TYPE = Link Width Switch Indicator,
AMCTL.CTRL_DETAIL = x2) indicating lanes 0 and 1 (TX2). The subsequent data flits are transmitted in
x2. In addition, the physical layer transmits the AMCTL with EEI on lanes 2 and 3. Then, lanes 2 and 3
transition to the electrical idle state and SerDes circuits such as the common-mode voltage are disabled.

5.B: Port B's physical layer receives the AMCTL indicating TX2 transmitted by port A. The subsequent
data flits are deskewed and unpacked in x2. The link width decreases from x4 to x2.




unifiedbus.com                                                                                              61
3 Physical Layer



Example 2: Link width increasing from TX2RX4 to TX4RX4




                             Figure 3-25 QDLWS link width increase process

Port A initiates a lane increase request to switch the TX width from x2 to x4.

1.A: Port A's data link layer transmits an LM block to port B to increase the TX width to x4. The LM
block carries Byte0.Bit0 = 1'b1 (Change TLW request) and Byte2.Bits[5:0] = 6'b000100 (TX Link
Width = x4).

2.B: Port B's data link layer receives the LM block from port A, parses each field, and determines that
lane increase is allowed. Then, port B SHALL transmit an LM block to port A to accept the lane increase
request. The LM block carries Byte1.Bit0 = 1'b1 (Change TLW request RSP = ACK) and
Byte3.Bits[5:0] = 6'b000100 (RX Link Width = x4). In addition, port B's physical layer directs lanes 2
and 3 to exit the electrical idle state and enables circuits such as the CDR and DFE to receive data.

If port B is not ready or does not allow the lane increase request from port A, it SHALL transmit an LM
block to port A to reject the lane increase request. The LM block carries Byte1.Bit0 = 1'b0 (Change
TLW request RSP = NAK) and Byte3.Bits[5:0] = 6'b000100 (RX link width = x2).

3.A: Port A's data link layer receives the LM block from port B, parses each field, and confirms that port
B has returned ACK.

If port A receives NAK from port B in the LM block, the process ends.




unifiedbus.com                                                                                            62
3 Physical Layer



4.A: Port A's data link layer directs its physical layer to initiate the lane increase process. The physical
layer continues to transmit the current data on lanes 0 and 1, directs lanes 2 and 3 to exit the electrical
idle state, and enables the TX circuits. After exiting the electrical idle state, lanes 2 and 3 continuously
transmit RLTBs. The RLTB field values (except RLTB.Type == Retrain.LP1_PHY_Up) are the same as
those in the Retrain.Active state (without data rate change and EQ request). Before transmitting RLTBs,
the AMCTL insertion interval SHALL be negotiated and switched to a short period. The default period is
one insertion every 640 symbols. The period is configurable, but the configured value SHALL ensure
that a continuous RLTB is not interrupted. During lane increase, AMCTLs SHALL be periodically
inserted into the lane that transmits data and the lane that transmits RLTBs based on the configured
short period.

4.B: Port B's RX continuously detects RLTBs on lanes 2 and 3, and checks whether the RLTB CRC is
correct. If eight consecutive RLTBs with correct CRC can be received, the data link layer SHALL
transmit an LM block to the peer end, indicating that lanes 2 and 3 of port B can operate properly. If
eight consecutive RLTBs with correct CRC cannot be received within a certain period of time T0 (T0 ==
2 ms), the physical layer is controlled to start RX adaptation to adjust RX parameters and continuously
detect RLTBs. If the RLTBs still cannot be received within T1 (T1 == 22 ms), the lane increase fails and
the process ends.

5.B: Port B's data link layer transmits an LM block to the peer end. The LM block carries Byte1.Bit2 =
1'b1 (RX lane up), indicating that lanes 2 and 3 of port B can operate properly.

6.A: After receiving the LM block (indicating port B's RX lanes 2 and 3 are ready) from port B's data link
layer, port A's data link layer transmits an AMCTL (AMCTL.CTRL_TYPE = Link Width Switch
Indicator, AMCTL.CTRL_DETAIL = x4) indicating lanes 0 to 3 (TX4). The subsequent data flits are
transmitted in x4.

6.B: Port B's physical layer receives the AMCTL indicating TX4 transmitted by port A. The subsequent
data flits are deskewed and unpacked in x4. The link width increases from x2 to x4. After the lane
increase is completed, the AMCTL insertion interval SHALL be negotiated and switched to the interval
before the lane increase.

Note: The port SHALL measure the time between initiating a lane increase or decrease request from its data link layer
and receiving a response through the LM block from the peer end. If this time exceeds T0 + T1 (24 ms), the lane
increase or decrease request is canceled, and the link reverts to the state before the lane increase or decrease request
was initiated.


3.4.2.4 Quick Link Width Degradation

UB supports quick link width degradation in the Link_Active state. The link width decrease process is
completed by the Remote TX Link Width Switch Indicator of the AMCTL. The LMSM does not need to
transition to the Retrain state. This reduces the time required for link width decrease. When this
mechanism is used, the following rules SHALL be met:

       1.    When the local RX lane detects an error on any lane, quick link width degradation can be
             performed only when RX lane 0 is normal. If RX lane 0 is abnormal, quick link width
             decrease SHALL be performed only when transitioning to the Retrain state.



unifiedbus.com                                                                                                         63
3 Physical Layer



      2.   On the side that initiates a link width decrease request, lane reversal SHALL not occur in its
           RX direction.
      3.   On the side that receives the link width decrease request, if the preceding rules are met, no
           ACK or NAK needs to be returned, and link width decrease is directly performed.
      4.   The RX on the initiator SHALL determine the target link width starting from lane 0, excluding
           the failed lanes. The target link width SHALL be a standard link width.

The following takes the damage of RX lane 3 on port B as an example to describe the link width
decrease process.




                   Figure 3-26 Quick link width decrease process in the Link_Active state

Step 1 The RX of port B periodically checks whether each lane receives an AMCTL. If AMCTLs fail to
       be detected on specific lanes (not lane 0) for N (0 < N < 255, custom, default to 3) consecutive
       times, quick link width decrease is triggered.

Step 2 Port B uses an AMCTL to initiate a quick link width decrease process on all active lanes.
       AMCTL.CTRL_TYPE is set to Remote TX Link Width Switch Indicator and
       AMCTL.CTRL_DETAIL is set to the target link width.

Step 3 Port A receives an AMCTL carrying Remote TX Link Width Switch Indicator on any active
       lane. Port A then decreases TX lanes at the local end based on AMCTL.CTRL_DETAIL. For
       example, to reduce the width to x2, port A transmits AMCTLs carrying AMCTL.CTRL_TYPE ==
       Link Width Switch Indicator and AMCTL.CTRL_DETAIL == x2 on lanes 0 and 1, and
       transmits AMCTLs with EEI on lanes 2 and 3 to direct the lanes to enter the electrical idle state.

Step 4 After receiving the link width decrease direction carried in the AMCTLs, port B performs deskew
       based on the indicated target width and receives data in x2.




unifiedbus.com                                                                                          64
3 Physical Layer



3.4.2.5 Data Rate Negotiation

UB links support data rate negotiation.

A link uses Data Rate 0 as the initial data rate to start link training. In the Discovery state, the ports SHALL
broadcast all supported data rates on all active TX lanes through DLTB.Data_Rate_Support_1 and
DLTB.Data_Rate_Support_2 (symbols 5 and 6). The ports at both ends of the link negotiate the data
rate through the LMSM and change to the common maximum data rate supported by both ends after the
Retrain state. If the data rate negotiation fails, the LMSM switches back to the original data rate.

A link in Optical-Link mode remains at a fixed data rate during and after link training, maintaining the
target data rate. For example, if the target data rate of such a link is 53.125 Gbit/s, this data rate is used
on all stages of link training.

A port supports only the same data rate for the TX and RX.


3.4.2.6 Lane Polarity Inversion

To facilitate board-level routing, UB supports lane polarity inversion so that the TX+ can be connected to
the peer RX-, while the TX- can be connected to the peer RX+. Lane polarity detection and inversion
occur in the Discovery state of link training. The AMCTL is used as the indicator of lane polarity inversion.

The AMCTL transmitted on each TX lane is not reversed. If the peer RX detects a reversed AMCTL on
any lane, the polarity of the lane SHALL be reversed. That is, the RX is responsible for lane polarity
detection and inversion.

In PAM4 mode, lane polarity inversion is completed before Gray decoding. During inversion, each bit is
reversed directly. See the following table.

                              Table 3-20 PAM4 lane polarity inversion example
 Original TX       TX Gray        TX       RX           Original RX       Reversed
                                                                                        RX Gray Decoding
 Data              Coding         Level    Level        Data              RX Data
 00                00             0        3            11                00            00
 01                01             1        2            10                01            01
 10                11             3        0            00                11            10
 11                10             2        1            01                10            11


3.4.2.7 Lane Reversal

In most cases, TX lane 0 of a port is connected to RX lane 0 of the peer end, and RX lane 0 of the port
is connected to TX lane 0 of the peer end.

However, in some cases, the lane connection order between ports can be reversed for the convenience
of board-level routing. For example, for an x4 link, TX0, TX1, TX2, and TX3 of port A are connected to
RX3, RX2, RX1, and RX0 of port B, respectively; while RX0, RX1, RX2, and RX3 of port A are
connected to TX3, TX2, TX1, and TX0 of port B, respectively.




unifiedbus.com                                                                                               65
3 Physical Layer



The port detects and adjusts the position of lane 0 during the Probe state. For details, see Section
3.4.3.2.

Both the primary and secondary ports should support lane reversal.


3.4.2.8 FEC/CRC Mode Switching

A port in the Link_Active state MAY measure the pre-FEC BER and enter the Retrain state to negotiate
and switch to the FEC/CRC mode that matches the current pre-FEC BER.

If a port detects that the current FEC/CRC mode does not match the current BER and intends to switch
to a matching mode, it SHALL initiate an FEC/CRC mode switching request. The peer port SHALL
accept or reject the switching request based on its measurement and judgment.

The following figure shows the FEC/CRC mode switching process.




                                Figure 3-27 FEC/CRC mode switching negotiation

Note 1: The port supports independent or concurrent switching of FEC and CRC modes.

Note 2: After switching, the data link layer SHALL ensure that the flow control interaction at both ends and the
generation and verification of BCRC are correct.

Note 3: The port uses the FEC or CRC mode field carried in the RLTBs for mode switching negotiation.




unifiedbus.com                                                                                                     66
3 Physical Layer



Note 4: The software allows the FEC or CRC mode to be changed by modifying the FEC or CRC mode at the
corresponding data rate in the PHY Link Control 6, 7, 8, and 9 registers in the configuration space, and then writing the
Retrain Link bit in the PHY Control 1 register. The subsequent steps are the same as those shown in the figure.


3.4.2.9 Link Equalization

For links operating at Data Rate 1 or higher, the link equalization mechanism adjusts the SerDes TX
and RX equalization parameters to improve the link signal quality.

All lanes of a link SHALL participate in the equalization process. Equalization is required when the data
rate is switched to Data Rate 1 or higher, unless the ports at both ends of the link declare that
equalization is not required.

The TX and RX of a port SHALL store the negotiated equalization parameters after the equalization
process is completed, so that these equalization parameters can be used when the link is switched to
this data rate again.

UB supports the following equalization modes, which are negotiated in the Config state.

Skip_EQ mode:

In this mode, the link directly switches from the initial data rate to the highest data rate supported by
both ends. The LMSM does not perform equalization at any data rate. This mode is used for links that
have executed equalization. The negotiated equalization parameters are stored at both ends to save
the link training time.

Only_Highest_Data_Rate_EQ mode:

In this mode, the link directly switches from the initial data rate to the highest data rate supported by both
ends, and equalization is performed only at the highest data rate. For example, if the data rates supported
by both ends are 2.578125 Gbit/s, 25.78125 Gbit/s, 53.125 Gbit/s, and 106.25 Gbit/s, the LMSM directly
switches from 2.578125 Gbit/s to 106.25 Gbit/s and performs equalization at 106.25 Gbit/s.

Full_EQ mode:

In this mode, the data rate SHALL be switched level by level until the highest data rate supported by
both ends is reached, and equalization is performed at each data rate greater than or equal to Data
Rate 1. For example, if the data rates supported by both ends are 2.578125 Gbit/s, 25.78125 Gbit/s,
53.125 Gbit/s, and 106.25 Gbit/s, the data rate SHALL be switched level by level from 2.578125 Gbit/s
to 25.78125 Gbit/s, 53.125 Gbit/s, and 106.25 Gbit/s, and equalization is performed at 25.78125 Gbit/s,
53.125 Gbit/s, and 106.25 Gbit/s.

A link in Optical-Link mode supports only the Skip_EQ mode, which SHALL be configured before link
training starts.

For an asymmetric link, the TX can use fixed equalization parameters, and the RX performs
equalization adaptation in the Equalization state.




unifiedbus.com                                                                                                          67
3 Physical Layer



3.4.3 LMSM
One or more lanes between ports form a link. Before link training is completed, the UBPUs at both ends
of the link SHALL not transmit any service data (flits). This section defines the LMSM, a hardware
mechanism that controls link training. Link training determines the link width, data rate, FEC mode, lane
reversal, and lane polarity, and trains the link to a state where service data can be transmitted and
received.

Each port at both ends of a link has an LMSM. After the power supply and clock signals are stable, the
reset signal or the software starts the LMSM for link training.

The LMSM supports training for electrical links and optical links.

The following figure shows the state transition of the LMSM.




                                      Figure 3-28 UB LMSM state transition

The following sections detail UB LMSM states.


3.4.3.1 Link_Idle

      ⚫     After exiting the reset, the LMSM enters the Link_Idle state, in which all TX lanes SHALL be
            in the electrical idle state.
      ⚫     The LMSM determines whether to bypass the Probe state based on the connection type
            between ports.
            −   AC coupling mode: The TX transmits detection pulses and uses the resistor-capacitor (RC)
                circuit to detect whether the peer RX exists. This mode does not bypass the Probe state.
            −   Optical-Link mode: The TX does not transmit detection pulses to detect whether the peer
                RX exists. This mode bypasses the Probe state.




unifiedbus.com                                                                                             68
3 Physical Layer



      ⚫    The variables are initialized as follows in this state:
           over_fibre_optical_enable is set to 1 in Optical-Link mode and to 0 in other cases.
           fix_data_rate_mode is set to 1 in Optical-Link mode or when the link does not support data
           rate change, and to 0 in other cases.
           bypass_equalization is set to 1 in Optical-Link mode and to 0 in other cases.
           bypass_Probe is set to 1 in Optical-Link mode or when Probe is not supported or required,
           and to 0 in other cases.
           Tx_M is equal to the value of the Target TX Link Width field in the PHY Link Control 1
           register.
           Rx_N is equal to the value of the Target RX Link Width field in the PHY Link Control 1
           register.
           Note: In PHY Mode-2, Tx_M is equal to Rx_N.

           LinkUp = 0
           LinkReady = 0
           change_speed = 0
           start_eq_init = 0
           symmetry_link = 0
           Retrain_num = 0
           If the Skip_EQ mode is not used (meaning EQ negotiation is required),
           eq_complete_data_rate1 to eq_complete_data_ratex are reset to 0.
           rx_lane0_id = 0
           tx_lane0_id = 0
           The TX lanes to be activated are lane Tx_0 to lane Tx_M – 1.
           The RX lanes to be activated are lane Rx_0 to lane Rx_N – 1.
      ⚫    The next state is Probe if bypass_Probe == 0, the PHY is ready, and the upper layer directs
           to transition to the next state.
      ⚫    The next state is RXEQ_Optimize if fix_data_rate_mode == 1, the PHY is ready, and the
           upper layer directs to transition to the next state.
      ⚫    The next state is Discovery if bypass_Probe == 1, fix_data_rate_mode == 0, the PHY is
           ready, and the upper layer directs to transition to the next state.
           "Upper layer directs to transition to the next state" means that an implementation-specific
           method is used to start the LMSM.


3.4.3.2 Probe

The Probe state aims to verify the presence of the RX at the far end of each lane and determine the
initial link width and the position of lane 0. In this state, the port transmits detection pulses through the
TX of each lane. Depending on whether there is termination at the RX, the RC value of the circuit
varies. The detection circuit in the TX can determine whether the far-end RX lane has termination by




unifiedbus.com                                                                                              69
3 Physical Layer



detecting the returned waveform. Based on the termination detection result at the far-end RX, the link
width in each direction can be preliminarily determined, along with the position of lane 0.

The Probe substates are described in the following sections.

Probe.Wait

      ⚫    All intended active TX lanes SHALL be in the electrical idle state.
      ⚫    All intended active RX lanes SHALL enable termination to ground.
      ⚫    The initial data rate of link training is Data Rate 0. If the data rate is not Data Rate 0 when
           the LMSM enters the Probe.Wait state, the LMSM SHALL stay in this substate for a certain
           period (determined by the implementation) and change the data rate to Data Rate 0 during
           this period.
      ⚫    If any of the following conditions is met, the next state is Probe.Confirm:
           −   Electrical idle exit detected on any intended active RX lane to be activated
           −   Timeout (determined by the implementation)
Probe.Confirm
      ⚫    After entering this state, the TX begins transmitting detection pulses on all TX lanes to be
           activated (on both the TX+ and TX-) to detect whether a termination resistor exists on the far-
           end RX. The detection result can be used to determine whether lane reversal is required.
      ⚫    If termination is detected on all TX lanes to be activated, the next state is Discovery.
      ⚫    If termination is not detected on any TX lane to be activated, the next state is Probe.Wait.
      ⚫    If termination is detected on at least one but not all TX lanes to be activated, the following
           actions are performed:
           −   Wait for a certain period of time (determined by the implementation).
           −   Send detection pulses again on all TX lanes to be activated.
               ▪ The next state is Discovery if the detection result is the same as the previous detection
                   result and the following operations are performed:
                   −   If no termination is detected on lane 0, lane reversal is performed based on the
                       detection result to reverse lane 0 to lane 1, 3, or 7 based on the TX link width.
                   −   Update the value of the Tx_M variable based on the final detection result for future use.
                       For example:
                       If termination is detected on lanes 1 to 7, lane 0 is reversed to lane 7 and the value
                       of Tx_M is updated to x4.
               ▪ Otherwise, the next state is Probe.Wait.
      ⚫    The activated TX lanes are lane Tx_0 to lane Tx_M – 1.
      ⚫    The values of the rx_lane0_id and tx_lane0_id variables are updated based on the current
           position of lane 0.




unifiedbus.com                                                                                               70
3 Physical Layer



3.4.3.3 RXEQ_Optimize

      ⚫   After transitioning to this state, both ends of the link exit the electrical idle state and the TX
          starts to transmit DLTBs and AMCTLs.
      ⚫   The RX detects AMCTLs for symbol lock. If necessary, the RX SHALL perform RX
          equalization adaptation on all RX lanes to be activated.
      ⚫   The DLTBs transmitted in this state are the same as those transmitted in the
          Discovery.Active state except that DLTB.Type = RXEQ_Optimize.
      ⚫   If either of the following conditions is met, the next state is Discovery.Active:
          −   RX equalization adaptation is completed on all RX lanes to be activated.
          −   This state times out.
              The timeout intervals are as follows:
              Data rate ≤ Data Rate 4: 48 ms
              Data Rate 4 < Data rate ≤ Data Rate 6: 72 ms
              Data Rate 6 < Data rate ≤ Data Rate 8: 120 ms


3.4.3.4 Discovery

Discovery.Active

      ⚫   After transitioning to this state, both ends of the link exit the electrical idle state and the TX
          starts to transmit DLTBs and AMCTLs on active lanes.
          Before exiting the electrical idle state and transmitting DLTBs, the TX SHALL wait until its
          common-mode voltage becomes stable.
      ⚫   The RX detects AMCTLs for symbol lock. If lane polarity inversion is detected, the lane
          polarity is adjusted accordingly.
      ⚫   The TX transmits DLTBs with the following features on all active TX lanes (all TX lanes are
          active if the Probe state is skipped):
          −   DLTB.Type is Discovery.Active.
          −   DLTB.Link_ID is set to a valid value for the primary port, and to NULL for the secondary
              port.
          −   DLTB.Lane_ID is the physical lane ID of the current lane.
          −   DLTB.TLW is set to the latest Tx_M.
          −   DLTB.RLW is set to Rx_N.
          −   DLTB.Data_Rate_Support_1 and DLTB.Data_Rate_Support_2 broadcast all supported
              data rates, including the ones that the port does not intend to use.
          −   DLTB.FEC_Mode_Support broadcasts all FEC modes supported by the port.
          −   DLTB.Port_Type is set to 1 for the primary port and 0 for the secondary port.
          −   If port type negotiation is not activated, DLTB.PortNego_Random_Value is set to NULL.
          −   DLTB.Lane_ID of logic lane 0 of the current link is set to 0.




unifiedbus.com                                                                                                 71
3 Physical Layer



      ⚫   If the received DLTB.Port_Type is the same as the transmitted one, port type negotiation is
          enabled. The port generates a 7-bit random number and fills it in the
          DLTB.PortNego_Random_Value field.
      ⚫   The active RX lanes are lane Rx_0 to lane Rx_N – 1.
      ⚫   The following variables are updated in real time based on the DLTB received on any active
          RX lane:
          −   Tx_M (Tx_M = Min{RX.DLTB.RLW, TX.DLTB.TLW})
          −   TX lane 0 may be reversed based on the RX_Lane0_ID value in the received eight
              consecutive DLTBs.
          −   The tx_lane0_id variable is updated based on the current TX lane 0.
      ⚫   If eight consecutive DLTBs that meet all the preceding conditions are not received on lane 0,
          RX lane 0 SHALL be reversed to lane 7, 3, or 1 based on the active RX lanes.
      ⚫   The next state is Discovery.Confirm if eight consecutive DLTBs are received on all active RX
          lanes, at least a certain number of DLTBs (256 DLTBs when entering this state from the
          Retrain state, and 1,024 DLTBs when entering from other states) are transmitted after one
          DLTB is received, and the received DLTBs meet all the following conditions:
          −   DLTB.Type is Discovery.Active or Discovery.Confirm.
          −   The received DLTB.Port_Type is different from the transmitted one.
          −   RX.DLTB.TLW is a standard link width and is less than or equal to Rx_N.
          −   RX.DLTB.RLW is a standard link width and is less than or equal to Tx_M.
      ⚫   Otherwise, the next state is Discovery.Confirm if eight consecutive DLTBs that meet all the
          following conditions are received on any active RX lane after a timeout (10 μs when
          transitioning to this state from the Retrain or Config state, or 24 ms when transitioning from
          other states):
          −   DLTB.Type is Discovery.Active or Discovery.Confirm.
          −   DLTB.TLW and DLTB.RLW are valid.
          −   At least 1,024 DLTBs are transmitted after one DLTB is received.
          −   The received DLTB.Port_Type is different from the transmitted one.
      ⚫   To transition from this state to another state, the following actions need to be performed:
          −   The rx_lane0_id variable is updated based on the current RX lane 0.
          −   The Rx_N variable is updated for future use: Rx_N = Min{RX.DLTB.TLW,
              TX.DLTB.RLW}.
      ⚫   If the transmitted DLTB.Port_Type is 1, the port is the primary port.
      ⚫   The active RX lanes are lane Rx_0 to lane Rx_N – 1.
      ⚫   Otherwise, the next state is Link_Idle.

Discovery.Confirm

      ⚫   The TX transmits DLTBs with valid link IDs on all active TX lanes.
          −   DLTB.Type is Discovery.Confirm.



unifiedbus.com                                                                                             72
3 Physical Layer



          −    When DLTB.Port_Type indicates the primary port, DLTB.Link_ID SHALL be set to a
               valid value. When DLTB.Port_Type indicates the secondary port, DLTB.Link_ID SHALL
               be set to the Link_ID value received from the active RX lane 0.
          −    DLTB.TLW is set to variable Tx_M.
          −    DLTB.RLW is set to variable Rx_N.
          −    DLTB.Data_Rate_Support_1 and DLTB.Data_Rate_Support_2 remain the same as
               those transmitted in the Discovery.Active state.
          −    DLTB.FEC_Mode_Support remains the same as that transmitted in the Discovery.Active
               state.
          −    DLTB.Port_Type is set to 1 for the primary port and 0 for the secondary port.
          −    DLTB.PortNego_Random_Value remains the same as that transmitted in the
               Discovery.Active state.
      ⚫   If eight consecutive DLTBs that meet the preceding conditions are received on any active RX
          lane but RX.DLTB.RLW != Tx_M:
           −   The port MAY reverse TX lane 0 based on RX_Lane0_ID in the received eight
               consecutive DLTBs.
           −   The Tx_M variable is updated: Tx_M = Min{RX.DLTB.RLW, TX.DLTB.TLW}.
           −   The tx_lane0_id variable is updated based on the current TX lane 0.
      ⚫   The next state is Config if eight consecutive DLTBs are received on all active RX lanes, at
          least 16 DLTBs are transmitted after one DLTB is received, and the received DLTBs meet all
          the following conditions:
          −    DLTB.Type is Discovery.Confirm.
          −    DLTB.Link_ID is the same as the transmitted one.
          −    RX.DLTB.TLW is a standard link width and is equal to Rx_N.
          −    RX.DLTB.RLW is a standard link width and is equal to Tx_M.
          −    RX.DLTB.Port_Type != TX.DLTB.Port_Type when port type negotiation is activated.
      ⚫   If Tx_M != Rx_N, the value of symmetric_link is 0. If Tx_M == Rx_N, the value of
          symmetric_link is 1.
      ⚫   Otherwise, the next state is Link_Idle after a timeout of 48 ms.


3.4.3.5 Config

Config.Active

      ⚫   The TX transmits CLTBs with valid link IDs on all active lanes determined in the Discovery
          state.
          −    CLTB.Type = Config.Active
          −    CLTB.TLW is set to variable Tx_M.
          −    CLTB.RLW is set to variable Rx_N.




unifiedbus.com                                                                                          73
3 Physical Layer



          −   The ID of each lane is set to a unique non-null value. In the same group of active lanes,
              the lane IDs are allocated in ascending order from Tx_0 to Tx_M – 1.
          −   CLTB.EQ_Mode is set based on the EQ Mode Control field of the PHY Link Control 2
              register.
      ⚫   The next state is Config.Check if two consecutive CLTBs are received on all active lanes with
          non-null link IDs and non-null lane IDs that match the IDs transmitted on the TX lanes of the
          local port (or match the reversed lane IDs if lane reversal is enabled), at least 16 CLTBs are
          transmitted after one CLTB is received, and the received CLTBs meet all the following
          conditions:
          −   CLTB.Type is Config.Active or Config.Check.
          −   The link ID is equal to the transmitted CLTB.Link_ID.
          −   The received CLTB.TLW is equal to variable Rx_N.
          −   The received CLTB.RLW is equal to variable Tx_M.
          −   The lane ID is a non-null value.
      ⚫   Otherwise, the next state is Link_Idle when any of the following conditions is met:
          −   2 ms timeout
          −   No link can be configured.
          −   Two consecutive DLTBs of the Discovery.Active type are received on all active lanes.

The primary port selects an FEC mode that is supported by both itself and the secondary port at the
current data rate, considering its own support and the mode broadcast by the secondary port.

The equalization mode is determined by the EQ_Mode values in the received two consecutive CLTBs
and the EQ_Mode value in the transmitted CLTB.

                             Table 3-21 Equalization mode negotiation table
       TX CLTB.EQ_Mode                     RX CLTB.EQ_Mode                    Equalization Mode
                 2'b00                            2'b00                              2'b00
                 2'b00                            2'b01                              2'b00
                 2'b00                            2'b10                              2'b00
                 2'b01                            2'b00                              2'b00
                 2'b01                            2'b01                              2'b01
                 2'b01                            2'b10                              2'b01
                 2'b10                            2'b00                              2'b00
                 2'b10                            2'b01                              2'b01
                 2'b10                            2'b10                              2'b10
                 2'b11                            2'bxx                              2'b00
                 2'bxx                            2'b11                              2'b00




unifiedbus.com                                                                                            74
3 Physical Layer



Config.Check

      ⚫   The TX transmits CLTBs with valid link IDs on all active lanes determined in the Discovery
          state.
          −   CLTB.Type = Config.Check
          −   CLTB.TLW is set to variable Tx_M.
          −   CLTB.RLW is set to variable Rx_N.
          −   The ID of each lane is set to a unique non-null value. In the same group of active lanes,
              the lane IDs are allocated in ascending order from Tx_0 to Tx_M – 1.
      ⚫   The next state is Config.Confirm if two consecutive CLTBs with non-null link IDs and non-null
          lane IDs that match those of the current port are received on all active lanes, at least 16
          CLTBs are transmitted after one CLTB is received, and the received CLTBs meet all the
          following conditions:
          −   CLTB.Type is Config.Check or Config.Confirm.
          −   The link ID is equal to the transmitted CLTB.Link_ID.
          −   The received CLTB.TLW is equal to variable Rx_N.
          −   The received CLTB.RLW is equal to variable Tx_M.
      ⚫   Otherwise, the next state is Link_Idle when any of the following conditions is met:
          −   2 ms timeout
          −   No link can be configured.
          −   Two consecutive DLTBs of the Discovery.Active type are received on all active lanes.

Config.Confirm

      ⚫   The TX transmits CLTBs with valid link IDs on all active lanes determined in the Discovery
          state.
          −   CLTB.Type = Config.Confirm
          −   CLTB.TLW is set to variable Tx_M.
          −   CLTB.RLW is set to variable Rx_N.
          −   The lane ID remains the same as that transmitted in the Config.Check state.
      ⚫   The next state is Send_NullBlock if two consecutive CLTBs with valid link IDs and non-null
          lane IDs that match those of the current port are received on all active lanes, at least 16
          CLTBs are transmitted after one CLTB is received, and the received CLTBs meet all the
          following conditions:
          −   CLTB.Type == Config.Confirm
          −   The link ID is equal to the transmitted CLTB.Link_ID.
          −   The received CLTB.TLW is equal to variable Rx_N.
          −   The received CLTB.RLW is equal to variable Tx_M.
      ⚫   The configured RX lanes are lane Rx_0 to lane Rx_N – 1.
      ⚫   The configured TX lanes are lane Tx_0 to lane Tx_M – 1.




unifiedbus.com                                                                                            75
3 Physical Layer



      ⚫   The LMSM transition SHALL occur at the boundary where AMCTLs are to be transmitted.
      ⚫   Otherwise, the next state is Link_Idle when any of the following conditions is met:
          −   2 ms timeout
          −   No link can be configured.
          −   Two consecutive DLTBs of the Discovery.Active type are received on all active lanes.


3.4.3.6 Send_NullBlock

      ⚫   If any of the following conditions is met, the next state is Discovery:
          −   The upper layer directs to transition to the Discovery state.
              Note 1: The upper layer direction means that the upper layer can optionally reconfigure the link width of
              the port.

              Note 2: The LMSM can increase or decrease the link width in this case, but the normal service data flow
              will be interrupted.

          −   Two consecutive DLTBs are received on any configured lane.
      ⚫   Otherwise:
          −   The TX transmits an AMCTL with SDF on all configured lanes to start data streams, and
              then transmits null blocks after the AMCTL.
              If the FEC mode is enabled, all the transmitted data streams SHALL be encoded by FEC.
              The FEC mode is determined in the Config state.
          −   The RX waits for null blocks.
          −   LinkUp = 1b
          −   The next state is Link_Active if eight consecutive null blocks are received on all
              configured lanes, at least 16 null blocks are transmitted after one null block is received,
              and all the following conditions are met:
              ▪    The null blocks are received after the AMCTL with SDF.
              ▪    Deskew between lanes SHALL be completed before data stream processing starts.
      ⚫   Otherwise, after a timeout of 2 ms:
          −   If the Retrain_num variable is less than FFh, the next state is Retrain.Active.

              Retrain_num is incremented by 1 each time the state transitions to Retrain.
          −   Otherwise, the next state is Link_Idle.


3.4.3.7 Link_Active

This is a normal operating state where data link layer packets can be transmitted.

      ⚫   LinkUp = 1b
      ⚫   To increase or decrease the link speed of the port, set the change_speed variable to 1b.
      ⚫   If an AMCTL with EDF is received on any configured lane, the next state is Retrain.Active.




unifiedbus.com                                                                                                       76
3 Physical Layer



          If an AMCTL with EDF is received on any configured lane, the RX data path SHALL stop
          processing data flits.
      ⚫   In the Link_Active state, if the current data rate is the common maximum data rate broadcast
          by both ends of the port in the Retrain state (or the common maximum data rate broadcast in
          the Discovery state if the Retrain state has not been entered prior to entering the Link_Active
          state, that is, Data Rate 0), the LinkReady variable is 1.
      ⚫   If any of the following conditions is met and an AMCTL with EDF is transmitted, the next state
          is Retrain.Active:
          −   The Retrain Link bit in the PHY Link Control 1 register is set to 1.
          −   The port is configured to enter the Discovery state to increase or decrease the link width
              using an implementation-specific method.
          −   change_speed = 1 (for speed change via a transition from Retrain to Change_Speed)
          −   If no AMCTL with EEI is received on any lane and the electrical idle state is detected or
              inferred, the port may transition to the Retrain.Active state.
          −   If the port detects an AMCTL error or any other types of framing errors, it may transition to
              the Retrain.Active state.


3.4.3.8 Retrain

Retrain.Active

      ⚫   LinkReady = 0
      ⚫   If the port is configured to perform or redo equalization with data rate change and the
          variable start_eq_init == 0, the TX transmits RLTBs with the following features on all
          configured lanes:
          −   RLTB.Type = Retrain.Active
          −   The equalization coefficients in the RLTBs are set to the values corresponding to the
              current data rate.
          −   If the port is configured to redo equalization, RLTB.Request_Equalization = 1.
          −   RLTB.Remote_Initial_TX_Preset is set to the value of the Remote_TX_Preset_Lanex
              field of the corresponding lane in the DATA_RATEx Control register for the next data rate.
          −   If the value of Remote_TX_Preset_Lanex of the corresponding lane in the
              DATA_RATEx Control register is Reserved or not supported, the TX uses an
              implementation-specific method to select a supported preset value.
          −   The secondary port broadcasts all the data rates it intends to use through
              RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2.
          −   The primary port broadcasts the target data rate and all the data rates lower than the target
              data rate through RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2. (For
              example, in PHY Mode-2 with Full_EQ enabled, when the primary and secondary ports
              support a common maximum data rate of 106.25 Gbit/s, the primary port sequentially
              targets 25.78125 Gbit/s, 53.125 Gbit/s, and 106.25 Gbit/s.)




unifiedbus.com                                                                                            77
3 Physical Layer



          −   If the port is configured to change the data rate or receives eight consecutive RLTBs carrying
              RLTB.Change_Speed == 1 on any configured lane, the variable change_speed = 1.
          −   If the variable change_speed == 1, RLTB.Change_Speed = 1.
          −   RLTB.FEC_Mode_Ctrl is set to the FEC mode to be used at the next data rate.
      ⚫   If the port is configured to change the data rate but does not want to perform or redo
          equalization and the variable start_eq_init == 0, the TX transmits RLTBs with the following
          features on all configured lanes:
          −   RLTB.Type = Retrain.Active
          −   The equalization coefficients in the RLTBs are set to the values corresponding to the
              current data rate.
          −   RLTB.Request_Equalization = 0
          −   RLTB.Remote_Initial_TX_Preset = 0
          −   The secondary port broadcasts all the data rates it intends to use through
              RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2.
          −   The primary port broadcasts the target data rate and all the data rates lower than the
              target data rate through RLTB.Data_Rate_Support_1 and
              RLTB.Data_Rate_Support_2. (For example, when the primary and secondary ports
              support a common maximum data rate of 106.25 Gbit/s in PHY Mode-2, an intended
              speed change to 53.125 Gbit/s requires the primary port to configure a target data rate of
              53.125 Gbit/s and lower, while 106.25 Gbit/s is not broadcast.)
          −   If the port is configured to change the data rate or receives eight consecutive RLTBs carrying
              RLTB.Change_Speed == 1 on any configured lane, the variable change_speed = 1.
          −   If the variable change_speed == 1, RLTB.Change_Speed = 1 is transmitted.
          −   RLTB.FEC_Mode_Ctrl is set to the FEC mode to be used at the next data rate.
      ⚫   If the port is configured to change the data rate and perform equalization, and the variable
          start_eq_init == 1, the TX transmits RLTBs with the following features on all configured lanes:
          −   RLTB.Type = Retrain.Active
          −   The equalization coefficients in the RLTBs are set to the values corresponding to the
              current data rate.
          −   RLTB.Request_Equalization = 0
          −   RLTB.Remote_Initial_TX_Preset = 0
          −   The secondary port broadcasts all the data rates it intends to use through
              RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2.
          −   The primary port broadcasts the current data rate and all the data rates lower than the
              current data rate through RLTB.Data_Rate_Support_1 and
              RLTB.Data_Rate_Support_2.
          −   change_speed = 0
          −   RLTB.FEC_Mode_Ctrl is set to the FEC mode used by the current port.




unifiedbus.com                                                                                            78
3 Physical Layer



      ⚫   If equalization needs to be performed or redone, the next state for the primary port is
          EQ.Coarsetune_Confirm, while the next state for the secondary port is
          EQ.Coarsetune_Active.
          −   Before entering the Equalization state, the port transmits no more than two RLTBs.
          −   The port at a certain data rate uses the TX preset value of the data rate to transmit data.
              The TX preset value of each lane at the data rate is determined according to the following
              rules:
              ▪ If eight consecutive RLTBs of the Retrain.EQ_Initial type that carry a valid TX preset
                   value are received in the latest Retrain.Confirm state, the TX preset value is used.
              ▪ If the TX preset value contained in the Local_TX_Preset_Lanex field of the
                   corresponding lane in the DATA_RATEx Control register is valid, the TX preset value
                   is used.
              ▪ Otherwise, the TX preset value is obtained using an implementation-specific method.
      ⚫   Otherwise:
          −   The TX transmits RLTBs with the following features on all configured lanes:
              ▪ RLTB.Type = Retrain.Active
              ▪ The equalization coefficients in the RLTBs are set to the values corresponding to the
                   current data rate.
              ▪ RLTB.Request_Equalization = 0
              ▪ RLTB.Remote_Initial_TX_Preset = 0
              ▪ The secondary port broadcasts all the data rates it intends to use through
                   RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2.
              ▪ The primary port broadcasts the current data rate and all the data rates lower than the
                   current data rate through RLTB.Data_Rate_Support_1 and
                   RLTB.Data_Rate_Support_2.
              ▪ RLTB.FEC_Mode_Ctrl is set to the FEC mode that the port intends to use at the
                   current data rate.
          −   change_speed = 0
          −   The TX uses the equalization coefficients negotiated in the latest equalization process.
          −   If the port transitions to this state from the Equalization state and receives a preset
              request in the EQ.Passive state, RLTB.Local_TX_Preset in the transmitted RLTBs is set
              to the latest preset value received in the EQ.Passive state.
      ⚫   The next state is Retrain.Confirm if eight consecutive RLTBs are received on all configured
          lanes, the value of RLTB.Change_Speed is equal to the value of change_speed, and at
          least 16 RLTBs are transmitted after one RLTB is received.
      ⚫   If the port enters this state from the Equalization state, the port evaluates the equalization
          coefficients or preset values in the RLTBs received on all lanes to determine whether they are
          the same as the final parameters negotiated in the Equalization state. If they are different, the
          value of RLTB.Request_Equalization transmitted in the Retrain.Confirm state is 1.
          The TX uses the equalization coefficients negotiated in the latest equalization process.



unifiedbus.com                                                                                             79
3 Physical Layer



      ⚫       If the following condition is met, the next state is Discovery:
              At least two consecutive DLTBs are received on any configured lane.
      ⚫       The primary port can evaluate the pre-FEC BER and renegotiate the FEC mode in this state.
              By measuring the pre-FEC BER of the link, the port can select the FEC mode that matches
              the current pre-FEC BER. The primary port can measure the pre-FEC BER by counting LTB
              CRC errors. The port SHALL meet the following requirements when measuring the pre-FEC
              BER to select the FEC mode:
              −    To measure the pre-FEC BER, the port sets RLTB.Pre-FEC_BER_Measurement_Status
                   to 2'b01.
              −    After completing the pre-FEC BER measurement and FEC mode selection, the port sets
                   RLTB.Pre-FEC_BER_Measurement_Status to 2'b10.

                   Note: The port SHALL complete the pre-FEC BER measurement and FEC mode selection within 22 ms.

              −    After the FEC mode is selected, the port broadcasts the selected FEC mode in RLTBs.
              −    If the port does not need to measure the pre-FEC BER and needs to use software to
                   configure the FEC mode, it sets RLTB.Pre-FEC_BER_Measurement_Status to 2'b00.
      ⚫       Otherwise, after a timeout of 24 ms:
              −    The next state is Retrain.Confirm if eight consecutive RLTBs carrying
                   RLTB.Change_Speed == 1 are received on any configured lane and the current data
                   rate is higher than Data Rate 0 or the common data rate broadcast in the transmitted and
                   received RLTBs is higher than the current data rate.
              −    The next state is Change_Speed if the current data rate is not changed to the target data
                   rate after the link enters the Retrain state and the current data rate is higher than Data
                   Rate 0. After exiting the Change_Speed state, the new data rate is Data Rate 0.
              −    The next state is Change_Speed if the current data rate is changed to the target data rate
                   after the link enters the Retrain state and the current data rate is higher than Data Rate 0.
                   Upon exit from the Change_Speed state, the data rate reverts to the data rate used prior
                   to entering the Retrain state.
              −    The next state is Discovery when the variable fix_data_rate_mode == 1 and at least two
                   consecutive RLTBs or DLTBs are received on any configured lane since the link enters
                   the Retrain.Active substate.
              −    The next state is Discovery when the variable fix_data_rate_mode == 0 and the following
                   conditions are met:
                   ▪ At least two consecutive RLTBs or DLTBs are received on any configured lane since
                      the link enters the Retrain.Active substate.
                   ▪ The current data rate is Data Rate 0.
                   ▪ The variable changed_speed_retrain == 0 and the received RLTB.Change_Speed == 0.
          −       Otherwise, the next state is Link_Idle.




unifiedbus.com                                                                                                  80
3 Physical Layer



Retrain.Confirm

      ⚫   If the port is configured to perform or redo equalization with data rate change and the
          variable start_eq_init == 0, the TX transmits RLTBs with the following features on all
          configured lanes:
          −   RLTB.Type = Retrain.EQ_Initial
          −   RLTB.Local_HS and RLTB.Local_LS of the current lane are set to the values used by
              the next data rate.
          −   If the port is configured to redo equalization, RLTB.Request_Equalization is set to 1.
          −   RLTB.Remote_Initial_TX_Preset is set to the value of the Remote_TX_Preset_Lanex
              field of the corresponding lane in the DATA_RATEx Control register for the next data rate.
          −   If the value of Remote_TX_Preset_Lanex of the corresponding lane in the
              DATA_RATEx Control register is Reserved or not supported, the TX uses an
              implementation-specific method to select a supported preset value.
          −   The secondary port broadcasts all the data rates it intends to use through
              RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2.
          −   The primary port broadcasts the target data rate and all the data rates lower than the
              target data rate through RLTB.Data_Rate_Support_1 and
              RLTB.Data_Rate_Support_2.
          −   If the port is configured to change the data rate or receives eight consecutive RLTBs carrying
              RLTB.Change_Speed == 1 on any configured lane, the variable change_speed = 1.
          −   If the variable change_speed == 1, RLTB.Change_Speed = 1 is transmitted.
          −   RLTB.FEC_Mode_Ctrl is set to the FEC mode to be used at the next data rate.
      ⚫   Otherwise, the TX transmits RLTBs with the following features on all configured lanes:
          −   RLTB.Type = Retrain.Confirm
          −   If the port is configured to redo equalization, RLTB.Request_Equalization is set to 1.
          −   The secondary port broadcasts all the data rates it intends to use through
              RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2.
          −   The primary port broadcasts the target data rate and all the data rates lower than the
              target data rate through RLTB.Data_Rate_Support_1 and
              RLTB.Data_Rate_Support_2.
          −   If the variable change_speed == 1, RLTB.Change_Speed = 1 is transmitted.
      ⚫   If all the following conditions are met, the TX transmits the RLTBs of the Retrain.EQ_Initial
          type on all configured lanes:
          −   The primary and secondary ports have broadcast Data Rate X (X > 0) in the Retrain and
              Discovery states, and receive eight consecutive RLTBs carrying RLTB.Change_Speed
              == 1 on any configured lane before entering this state.
          −   The variable eq_complete_data_ratex (x > 0) is 0, the Perform Equalization field of the
              PHY Link Control 2 register is 1, or an implementation-specific mechanism determines
              that equalization needs to be performed.




unifiedbus.com                                                                                            81
3 Physical Layer



          −   The current data rate is lower than Data Rate X (X > 0).
      ⚫   After entering this substate, start_eq_init = 0.
      ⚫   If all the following conditions are met, the next state is Change_Speed:
          −   Eight consecutive RLTBs of the Retrain.Confirm or Retrain.EQ_Initial type carrying
              RLTB.Change_Speed == 1 are received on any configured lane.
          −   After an RLTB carrying RLTB.Change_Speed == 1 is received, 128 RLTBs carrying
              RLTB.Change_Speed = 1 are transmitted on the same configured lane.
          −   The current data rate is higher than Data Rate 0, or the maximum data rates broadcast in
              the transmitted RLTBs and at least eight consecutive received RLTBs are higher than
              Data Rate 0.
          The new data rate changed in the Change_Speed state is the common maximum data rate
          supported by the ports at both ends of the link.
          If the data rate is Data Rate 1 or higher and start_eq_init == 1:
          −   When transmitting at a data rate requiring equalization, the secondary port SHALL apply
              the TX preset value obtained from the eight consecutive RLTBs received in the
              Retrain.Confirm state. The port SHALL ensure that its TX settings conform to the preset
              parameter definition.
          −   When data is transmitted at the data rate where equalization is to be performed, the lane
              that receives Reserved or an unsupported preset value uses an implementation-specific
              method to select a valid preset value for its TX to transmit the pattern.
      ⚫   If any of the following conditions is met, the next state is Discovery:
          −   Eight consecutive DLTBs are received on any configured lane.
          −   The upper layer directs to transition to the Discovery state.
              The upper layer direction means that the upper layer sets the Retrain Link bit in the PHY
              Link Control 1 register to reconfigure the link width.
              When entering the Discovery state, the changed_speed_retrain variable is set to 0.
      ⚫   If all the following conditions are met, the next state is Send_NullBlock:
          −   Eight consecutive RLTBs of the Retrain.Confirm type are received on all configured lanes,
              data rate identifiers (RLTB.Data_Rate_Support_1 and RLTB.Data_Rate_Support_2)
              are identical on all lanes, and one of the following conditions is met:
              ▪ RLTB.Change_Speed == 0 in the received eight consecutive RLTBs.
              ▪ The current data rate is Data Rate 0, and no data rate higher than Data Rate 0 is
                   broadcast in the received or transmitted RLTBs.
          −   After one RLTB is received, 16 RLTBs that are not interrupted by AMCTLs are transmitted.
          −   AMCTLs with SDF are to be transmitted.
           When entering the Send_NullBlock state, the changed_speed_retrain and change_speed
           variables are reset to 0.
      ⚫   The port SHALL check whether the peer end has performed pre-FEC BER measurement
          and FEC mode negotiation in the previous state.




unifiedbus.com                                                                                        82
3 Physical Layer



          If performed, and the gain of the received FEC mode is lower than the required threshold
          (that is, the FEC mode provides insufficient error correction capability), the port SHALL adopt
          the default FEC mode, reflect the default FEC mode in the RLTB.FEC_Mode_Ctrl field, and
          set RLTB.FEC_Mode_Reject to 1.
          Otherwise, the port uses the FEC mode specified by the peer end, reflects the FEC mode in the
          RLTB.FEC_Mode_Ctrl field, and sets RLTB.FEC_Mode_Reject to 0 in transmitted RLTBs.
          When receiving RLTB.FEC_Mode_Reject == 1, the peer end uses the default FEC mode.
          The default FEC mode is RS(128,120,T=4).
      ⚫   The next state is Change_Speed if the data rate has been changed to the common
          negotiated data rate since transitioning from Link_Active to Retrain, an AMCTL with EEI has
          been received or electrical idle is detected or inferred on any configured lane, and no RLTB
          of the Retrain.Confirm type has been received on any configured lane since transitioning to
          Retrain.Confirm.
          After exiting the Change_Speed state, the data rate changes back to that at the transition
          from Link_Active to Retrain.
      ⚫   The next state is Change_Speed if the data rate has not been changed to the common
          negotiated data rate since transitioning from Link_Active to Retrain, an AMCTL with EEI has
          been received or electrical idle is detected or inferred on any configured lane, and no RLTB
          of the Retrain.Confirm or Retrain.EQ_Initial type has been received on any configured lane
          since transitioning to Retrain.Confirm.
          After exiting the Change_Speed state, the data rate changes to Data Rate 0.
      ⚫   Otherwise, after a timeout of 48 ms:
           −   The next state is Discovery if fix_data_rate_mode == 1 and at least two consecutive
               RLTBs or DLTBs have been received on any configured lane since entering the
               Retrain.Confirm substate.
           −   The next state is Discovery if fix_data_rate_mode == 0 and all the following conditions
               are met:
               ▪ At least two consecutive RLTBs or DLTBs are received on any configured lane since
                   entering the Retrain.Confirm substate.
               ▪ The current data rate is Data Rate 0.
               ▪ The variable changed_speed_retrain == 0 and the received RLTB.Change_Speed == 0.
           −   The next state is Send_NullBlock if the variable Retrain_num is less than 0xFF and the
               current data rate is greater than Data Rate 0.
               After entering the Send_NullBlock state, changed_speed_retrain = 0.
           −   Otherwise, the next state is Link_Idle.


3.4.3.9 Change_Speed

This state is not supported in Optical-Link mode.

      ⚫   The TX enters the electrical idle state after sending an AMCTL with EEI.




unifiedbus.com                                                                                           83
3 Physical Layer



            −    If the data rate change is successful, the TX remains in the electrical idle state for a
                 certain period of time (determined by the implementation).
            −    If the data rate change fails, the TX remains in the electrical idle state for a certain period
                 of time (determined by the implementation, but greater than the time when the data rate
                 change is successful).
       ⚫    A transition to a new data rate is permitted only after the RX has entered the electrical idle
            state and the TX is no longer required to maintain electrical idle based on the
            aforementioned conditions.
            Note: If the link is already operating at the highest supported data rate, the state transitions to
            Change_Speed, but the data rate does not change.
       ⚫    After the data rate is successfully changed, the next state is Retrain.Active. The new data
            rate is determined according to the following rules:
            −    If the state transitions from Retrain.Confirm and the data rate is successfully changed, the
                 new data rate is the common maximum data rate broadcast by both ends of all configured
                 lanes and the changed_speed_retrain variable is 1.
            −    If this is the second entry into Change_Speed since the transition from Link_Active to
                 Retrain, the new data rate is the data rate at which the state transitions from Link_Active
                 to Retrain, and the changed_speed_retrain variable is 0.
            −    Otherwise, the new data rate changes to Data Rate 0, and the changed_speed_retrain
                 variable is 0.
       ⚫    The change_speed_retrain variable is 0. The new data rate is reflected in the Current Link
            Speed field of the PHY Link Status 1 register.
       ⚫    Otherwise, the next state is Link_Idle after a timeout of 48 ms.


3.4.3.10 Equalization

EQ.Coarsetune_Active

When entering this substate, the following fields in the State 1 register at the current data rate SHALL
be set to 0: Equalization Coarsetune Phase Complete, Equalization Active Phase Successful,
Equalization Passive Phase Successful, and Equalization Complete.

The following variables SHALL be set to 0: eq_complete_data_rate1 to eq_complete_data_ratex
(eq_complete_data_ratex is determined by the highest data rate supported by the port), and
start_eq_init.

Note: If the RX lane sequence is different from the TX lane sequence, the equalization information should be reversed
during equalization.

       ⚫    The TX transmits ELTBs with the following features on all configured lanes:
            −    ELTB.Type = Equalization
            −    ELTB.Current_EQ_Phase = Coarsetune_Active




unifiedbus.com                                                                                                          84
3 Physical Layer



           −     The TX_Preset field of each lane is set to the TX preset value corresponding to the
                 current data rate.
           −     The pre-cursor and post-cursor fields of each lane are set to the TX pre-cursor and post-
                 cursor coefficients corresponding to the current data rate.
      ⚫    Once in this state, the port is allowed to wait for a certain period of time (determined by the
           implementation) before evaluating the received data.
           The next state is EQ.Coarsetune_Confirm if the RX has completed AMCTL locking and two
           consecutive ELTBs that meet all the following conditions are received on all configured lanes:
           −     ELTB.Type == Equalization
           −     ELTB.Current_EQ_Phase == Coarsetune_Confirm
           −     If necessary, the RX completes RX equalization adaptation.
      ⚫    Otherwise, after a timeout of 12 ms:
           −     The next state is EQ.Coarsetune_Confirm if the bit corresponding to the current data rate
                 indicated by the Skip EQ Coarsetune Enable field in the PHY Link Control 11 register is 1.
           −     Otherwise, the next state is Change_Speed.
                 ▪   successful_speed_change = 0
                 ▪   Equalization Complete = 1 and Equalization Coarsetune Phase Complete = 1 in
                     the State 1 register at the corresponding data rate

EQ.Coarsetune_Confirm

When entering this substate, the following fields in the State 1 register at the current data rate SHALL
be set to 0: Equalization Coarsetune Phase Complete, Equalization Active Phase Successful,
Equalization Passive Phase Successful, and Equalization Complete.

The following variables SHALL be set to 0: eq_complete_data_rate1 to eq_complete_data_ratex
(eq_complete_data_ratex is determined by the highest data rate supported by the port), and
start_eq_init.

      ⚫    The TX transmits ELTBs with the following features on all configured lanes:
           −     ELTB.Type = Equalization
           −     ELTB.Current_EQ_Phase = Coarsetune_Confirm
           −     The TX_Preset field of each lane is set to the TX preset value corresponding to the
                 current data rate.
           −     The pre-cursor and post-cursor fields of each lane are set to the TX pre-cursor and post-
                 cursor coefficients corresponding to the current data rate.

For the primary port:

      ⚫    Once in this state, the port is allowed to wait for a certain period of time (determined by the
           implementation) before evaluating the received data.
      ⚫    The next state is EQ.Passive if the RX has completed AMCTL locking and two consecutive
           ELTBs that meet all the following conditions are received on all configured lanes, and the
           port needs to perform the EQ.Active and EQ.Passive phases:



unifiedbus.com                                                                                               85
3 Physical Layer



          −   ELTB.Type == Equalization
          −   ELTB.Current_EQ_Phase == Coarsetune_Confirm
          −   If necessary, the RX completes RX equalization adaptation.
          Before transitioning to the EQ.Passive state, the following bits of the State 1 register at the
          current data rate are set to 1: Equalization Coarsetune Phase Complete and Equalization
          Coarsetune Phase Successful.
      ⚫   Otherwise, the next state is Retrain.Active if the RX has completed AMCTL locking and two
          consecutive ELTBs that meet all the following conditions are received on all configured lanes,
          and the port does not need to perform the EQ.Active and EQ.Passive phases:
          −   ELTB.Type = Equalization
          −   ELTB.Current_EQ_Phase = Coarsetune_Confirm
          −   If necessary, the RX completes RX equalization adaptation.
          Before transitioning to the Retrain.Active state, the following bits of the State 1 register at the
          current data rate are set to 1: Equalization Coarsetune Phase Complete, Equalization
          Coarsetune Phase Successful, Equalization Active Phase Successful, Equalization
          Passive Phase Successful, and Equalization Complete.
      ⚫   Otherwise, after a timeout of 24 ms:
          −   The next state is EQ.Passive if the bit corresponding to the current data rate indicated by
              the Skip EQ Coarsetune Enable field in the PHY Link Control 11 register is 1.
              Before transitioning to the EQ.Passive state, the following bits of the State 1 register at
              the current data rate are set to 1: Equalization Coarsetune Phase Complete and
              Equalization Coarsetune Phase Successful.
          −   Otherwise, the next state is Change_Speed.
              successful_speed_change = 0
              The Equalization Coarsetune Phase Complete and Equalization Complete bits of the
              State 1 register at the current data rate are set to 1.

For the secondary port:

      ⚫   The next state is EQ.Active if two consecutive ELTBs that meet all the following conditions
          are received on all configured lanes:
          −   ELTB.Type == Equalization
          −   ELTB.Current_EQ_Phase == Passive_Phase
          Before transitioning to the EQ.Active state, the following bits of the State 1 register at the
          current data rate are set to 1: Equalization Coarsetune Phase Complete and Equalization
          Coarsetune Phase Successful.
      ⚫   Otherwise, the next state is Retrain.Active if eight consecutive RLTBs are received on all
          configured lanes.
          Before transitioning to the Retrain.Active state, the following bits of the State 1 register at the
          current data rate are set to 1: Equalization Coarsetune Phase Complete, Equalization
          Coarsetune Phase Successful, and Equalization Complete.



unifiedbus.com                                                                                              86
3 Physical Layer



      ⚫   Otherwise, after a timeout of 12 ms:
          −   The next state is EQ.Active if the bit corresponding to the current data rate indicated by
              the Skip EQ Coarsetune Enable field in the PHY Link Control 11 register is 1 and the
              port intends to perform the EQ.Active and EQ.Passive phases.
              Before transitioning to the EQ.Active state, the following bits of the State 1 register at the
              current data rate are set to 1: Equalization Coarsetune Phase Complete and
              Equalization Coarsetune Phase Successful.
          −   Otherwise, the next state is Change_Speed.
              successful_speed_change = 0
              The Equalization Coarsetune Phase Complete and Equalization Complete bits of the
              State 1 register at the current data rate are set to 1.

After the EQ.Coarsetune_Confirm phase is completed, the BER of the primary and secondary ports
SHALL be less than 10-4.

EQ.Passive

      ⚫   The TX transmits ELTBs with the following features on all configured lanes:
          −   ELTB.Type = Equalization
          −   ELTB.Current_EQ_Phase is set to Passive_Phase.
      ⚫   If two consecutive ELTBs carrying ELTB.Current_EQ_Phase == Active_Phase are received:
          −   If the preset value or the set of coefficients in the received ELTBs is legal:
              ▪ The TX's equalization setting is changed to the required preset value or coefficients,
                   and the new equalization value takes effect on the TX pin within a certain period of
                   time (determined by the implementation).
              ▪ If a preset value is requested in the transmitted ELTBs, ELTB.Preset_Mode_En = 1. If
                   a set of coefficients is requested, ELTB.Preset_Mode_En = 0. For both requests, the
                   pre-cursor and post-cursor fields are set to the values corresponding to the TX's
                   current equalization setting. ELTB.EQ_Reject = 0
          −   If the preset value or the set of coefficients in the received ELTBs is illegal:
              ▪ The TX's equalization setting is not changed.
              ▪ If a preset value is requested in the transmitted ELTBs, ELTB.Preset_Mode_En = 1.
                   If a set of coefficients is requested, ELTB.Preset_Mode_En = 0. If the pre-cursor
                   and post-cursor values reflect the requested preset value or coefficients,
                   ELTB.EQ_Reject = 1.
      ⚫   For the primary port, if two consecutive ELTBs carrying ELTB.Current_EQ_Phase ==
          Passive_Phase are received on all configured lanes, the next state is EQ.Active.
          Equalization Passive Phase Successful in the State 1 register at the current data rate is
          set to 1.
      ⚫   If two consecutive RLTBs are received on all configured lanes, the next state is
          Retrain.Active.




unifiedbus.com                                                                                             87
3 Physical Layer



            −   Equalization Passive Phase Successful in the State 1 register at the current data rate
                is set to 1.
            −   The TX's equalization SHALL be set to the latest received legal value.
      ⚫     After a timeout (32 ms for data rates less than or equal to Data Rate 4 and 64 ms for data
            rates greater than Data Rate 4), the next state is Change_Speed.
            −   successful_speed_change = 0
            −   Equalization Complete in the State 1 register at the current data rate is set to 1.

EQ.Active

      ⚫     The TX transmits ELTBs with the following features on all configured lanes:
            −   ELTB.Type is Equalization.
            −   ELTB.Current_EQ_Phase = Active_Phase
      ⚫     If the port is in Optical-Link mode, it SHALL not perform remote FFE training but SHALL
            perform RX CTLE adaptation.
      ⚫     If the port is not in Optical-Link mode, it needs to independently perform equalization
            evaluation on each configured lane according to the following requirements:
            −   If a preset value is requested, ELTB.Preset_Mode_En is set to 1 and
                ELTB.Request_TX_Preset is set to the preset value to be evaluated in the transmitted
                ELTBs.
            −   If a set of coefficients is requested, ELTB.Preset_Mode_En is set to 0 and the pre-cursor
                and post-cursor fields are set to the values to be evaluated in the transmitted ELTBs.
            −   Once a new equalization setting evaluation request is updated, it SHALL be retained for a
                certain period of time (determined by the implementation) or until the evaluation is
                completed.
            −   A certain period of roundtrip delay (determined by the implementation) is allowed to
                ensure that the peer port (port in the EQ.Passive state) has used the requested
                equalization setting to transmit streams after receiving the request. Then the local port
                can evaluate the current setting by receiving the streams.
            −   If two consecutive ELTBs that meet the following conditions are received:
                ▪   ELTB.Current_EQ_Phase == Passive_Phase
                ▪   ELTB.EQ_Reject == 0
                ▪   The value of ELTB.Request_TX_Preset (when a preset value is requested) or the
                    values of the pre-cursor and post-cursor fields are equal to the equalization value
                    requested by the local end.
                This indicates that the peer port has accepted the requested equalization value, and the
                local RX can start to evaluate the current equalization setting.
                The current equalization setting can be considered as a candidate final equalization
                setting. If the current equalization setting is not selected as the final equalization setting,
                the port can attempt to evaluate the next equalization setting.




unifiedbus.com                                                                                                88
3 Physical Layer



          −   If two consecutive ELTBs that meet the following conditions are received:
              ▪    ELTB.Current_EQ_Phase == Passive_Phase
              ▪    ELTB.EQ_Reject == 1
              ▪    The value of ELTB.Request_TX_Preset (when a preset value is requested) or the
                   values of the pre-cursor and post-cursor fields are equal to the equalization value
                   requested by the local end.
              This indicates that the peer port has rejected the requested equalization value, and the
              local RX does not evaluate the current equalization setting.
              The current equalization setting cannot be considered as a candidate final equalization
              setting, and the port can attempt to evaluate the next equalization setting.
          −   If the RX does not receive two consecutive ELTBs carrying ELTB.Current_EQ_Phase ==
              Passive_Phase within 2 ms and the current state has not reached the 24 ms timeout, the
              port needs to drop the current equalization setting and start to transmit the next
              equalization setting request.
          −   The port SHALL complete all equalization setting evaluations within 24 ms.
      ⚫   For the primary port, if all configured lanes reach the optimized equalization setting and the
          RX equalization adaptation is completed (if necessary), the next state is Retrain.Active.
          The Equalization Active Successful and Equalization Complete bits in the State 1
          register at the current data rate are set to 1.
      ⚫   For the secondary port, if all configured lanes reach the optimized equalization setting and
          the RX equalization adaptation is completed (if necessary), the next state is EQ.Passive.
          The Equalization Active Successful and Equalization Complete bits in the State 1
          register at the current data rate are set to 1.
      ⚫   After a timeout (24 ms for data rates less than or equal to Data Rate 4 and 48 ms for data
          rates greater than Data Rate 4, with the timeout tolerance ranging from 0 ms to 2 ms), the
          next state is Change_Speed.
          −   successful_speed_change = 0
          −   Equalization Complete in the State 1 register at the current data rate is set to 1.




unifiedbus.com                                                                                           89
