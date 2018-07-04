% makeLPHPFilters

ch = 2;
N = 2048;

B1 = fir1(N-1,0.025);
B2 = fir1(N-1,0.025,'high');

L1_01 = B1';
L1_02 = B1';
save('l1_LP','L1_01','L1_02')

R1_01 = B2';
R1_02 = B2';
save('R1_HP','R1_01','R1_02')

