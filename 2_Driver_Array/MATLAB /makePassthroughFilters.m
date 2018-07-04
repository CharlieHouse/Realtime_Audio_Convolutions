% makePassThroughFilters

ch = 2;
N = 2048;

h = zeros(ch,N);
h(:,1) = 1;

L1_01 = h(1,:)';
L1_02 = h(2,:)';
save('l1_passthrough','L1_01','L1_02')

R1_01 = h(1,:)';
R1_02 = h(2,:)';
save('R1_passthrough','R1_01','R1_02')
