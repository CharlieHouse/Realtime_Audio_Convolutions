% makeBinauralFilters
% Uses HRIR data from the listen database
% 
% Data is filtered using four HRIRS. 
% 
% loudspeaker 1 is in the left ear. This hears: 
%   signal 1 filtered from 30 degrees to the left 
%   signal 2 filtered from 30 degrees to the right
%
% loudspeaker 2 is in the right ear. This hears:
%   signal 1 filtered from 30 degrees to the left
%   signal 2 filtered from 30 degrees to the right 
% 
%       S1                        S2
%          `                    `   
%            `      - ^ -     `
%              `  /       \ `
%                (         )
%                 \       /
%                   - - -

load('IRC_1002_C_HRIR.mat') % load HRIR mat file

% impulse response from source 30 deg to the left, heard at left ear
idxLL = find(and(l_eq_hrir_S.azim_v ==30, l_eq_hrir_S.elev_v == 0));
% impulse response from source 30 deg to the right, heard at left ear
idxLR = find(and(l_eq_hrir_S.azim_v ==330, l_eq_hrir_S.elev_v == 0));
% impulse response from source 30 deg to the left, heard at right ear
idxRL = find(and(r_eq_hrir_S.azim_v ==30, l_eq_hrir_S.elev_v == 0));
% impulse response from source 30 deg to the right, heard at right ear
idxRR = find(and(r_eq_hrir_S.azim_v ==330, l_eq_hrir_S.elev_v == 0));

% get filters
% IR = Impulse Response, L|R = ear, L
IRLL = l_eq_hrir_S.content_m(idxLL,:);
IRLR = l_eq_hrir_S.content_m(idxLR,:);
IRRL = r_eq_hrir_S.content_m(idxRL,:);
IRRR = r_eq_hrir_S.content_m(idxRR,:);

figure(1)
subplot(2,1,1)
plot(IRLL)
hold on
plot(IRLR)
legend('Left source to left ear','Right source to left ear')
subplot(2,1,2)
plot(IRRL)
hold on
plot(IRRR)
legend('Left source to right ear','Right source to right ear')

% filter length required
N = 2048; 
pad = N-length(IRRR);
% pad up to length
IRLL = [IRLL,zeros(1,pad)];
IRLR = [IRLR,zeros(1,pad)];
IRRL = [IRRL,zeros(1,pad)];
IRRR = [IRRR,zeros(1,pad)];

% save 
% audio from source 1 is filtered by L1_xx
L1_01 = IRLL';
L1_02 = IRLR';
save('../FILTERS/l1_bin','L1_01','L1_02')

% audio from source 2 is filtered by R1_xx
R1_01 = IRRL';
R1_02 = IRRR';
save('../FILTERS/R1_bin','R1_01','R1_02')

