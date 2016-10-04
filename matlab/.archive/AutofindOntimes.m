%% Autogenerated Motormaps
%% this script runs ONLY on the testbedcomputer
close all
clear all

%% INPUTS
% Specify Stage
stage = 'stage1';

% Define test directory with folders containing the streak images
topdir = 'D:\PfsTests\06_04_14_11_06_47_ThetaFWD_Ontime\Images/';

% Specify number of buckets (leave at 100 if unsure)
numBuckets = 100;

% bw threshold will be bwfactor*mean(img)
bwfactor = 1; % reduce this if your circles dont appear fully on the bw image.

% Sensitivity of Hough transform circle detection (higher will detect more
% circles) range is between 0 and 1
circSnstvty = 0.9;

%Define the Range in which the Circle-Radii are. (in px)
radiusRange = [40, 120];

%% EXECUTION
images = dir2cell([topdir '*.fits']);
notok = true;
while notok
    
    intensities.pId1 = [];
    intensities.pId2 = [];
    intensities.pId3 = [];
    intensities.pId4 = [];
    intensities.pId5 = [];
    intensities.pId6 = [];
    intensities.pId7 = []; 
    intensities.pId8 = [];
    intensities.pId9 = [];
    
    hardstops.pId1 = [];
    hardstops.pId2 = [];
    hardstops.pId3 = [];
    hardstops.pId4 = [];
    hardstops.pId5 = [];
    hardstops.pId6 = [];
    hardstops.pId7 = [];
    hardstops.pId8 = [];
    hardstops.pId9 = [];
    
    overloads = [];
    imageMatrix = [];
    
    
    % Look for image with streak to find centers
    for nim = [1:length(images)]
        imagefile = char(strcat(topdir,images(nim)));
        if(strfind(imagefile, 'cntrStrk'))
            fitsfile =imagefile;
            % centerImage = strcat(topdir, 'streaks2rv_ImageId_1582_Target_99_Iteration_41_loopId_7_64.fits')
        elseif  (strfind(imagefile, 'streaks2rv_'))
            fitsfile =imagefile;
        elseif  (strfind(imagefile, 'centerStrk_'))
            fitsfile =imagefile;
        end
    end
    img = imread(fitsfile);
    imgsize = size(img);
    
    % Use initial bwfactor to create bw thresholded image
    imrs = reshape(img, 1, 2048*2048);
    myLowerThresh = bwfactor* mean(imrs);
    clear imrs;
    bw_mine  = (img > myLowerThresh);
    figure(1), imagesc(bw_mine);
    hold on;
    
    % Find centers and radii
    [centers, radii] = imfindcircles(bw_mine, radiusRange,'ObjectPolarity','bright', 'Sensitivity' , circSnstvty);
    [r, c, rad] = circlefinder(bw_mine, radiusRange(1), radiusRange(2), 0.13);
    if(~isempty(centers))
        crm = horzcat(centers, radii);
        crm = sortrows(crm, 1);
        crm = flipud(crm);
        crm = horzcat(crm(:,1) + 1i * crm(:,2), crm(:,3));
         %cs = centers(:,1) + centers(:,2) * 1i;
    else
        cs = c + r * 1i;
        radii = rad;
        crm = horzcat(cs, radii);
        crm = sortrows(crm);
        crm = flipud(crm);
    end
    
    if(isempty(crm))
    else
        plot(crm(:,1), 'r*');
    end
    
    
    % Create Window to /Check
    % Construct a questdlg with three options
    choice = questdlg('Are all positioner centers found?', ...
        'Center Check in Figure 1', ...
        'Yes','No, the circles are to faint', 'No, the circles are to thick','No, the circles are to thick');
    % Handle response
    switch choice
        case 'Yes'
            disp([choice ' coming right up.'])
            notok = false;
        case 'No, the circles are to faint'
            disp([choice '. So I will decrease threshold and rerun.'])
            bwfactor = bwfactor/2;
        case 'No, the circles are to thick'
            disp('I''ll increase threshold and rerun.')
            bwfactor = bwfactor*2;
    end
end


%% Calculate Intensity

% Angular size of the pie:
resolution_angle=2*pi/numBuckets;
angles=[resolution_angle:resolution_angle:2*pi];
check = 0;
cc=1;

% Create figure for ontime comparisons
otfh = figure('Name','OnTime Tuning');
otfhs1 = subplot(1,2,1);
prv = allchild(otfhs1);
axis equal;
otfhs2 = subplot(1,2,2);
axis equal;
uicontrol('Style', 'pushbutton', 'String', 'Select this on-time',...
        'Position', [20 20 50 20],...
        'Callback', 'tcc=cc;return @break;');

for ps = 1:length(crm(:,1))
    for nDir = [1:length(images)-0]
        
        disp(strcat('Now processing',images(nDir)));
        imagefile = char(strcat(topdir,images(nDir)));
        
        %Read Intensity
        imageMatrix=imread(imagefile);
        S = images(nDir);
        trex = regexp(S,'(?<=ontime_)\d*','match');
        if isempty(trex{1})
            continue  
        end
        
        A = regexp(S,'ImageId_\d*','match');
        ontimes(cc) = str2num(trex{1}{1});
        isRV = true;
        
        
        use = true;
        pid = sprintf('pId%d',ps) ;
        cobracenter = crm(ps,1);
        min_range = floor(crm(ps,2)) - 10;
        max_range = floor(crm(ps,2)) + 8;
        [intensity.(pid), overload ] = getIntensityN( cobracenter, min_range, max_range, imageMatrix, resolution_angle, topdir, nDir, numBuckets, ontimes(cc), ps);
        
        if(check < 1)
            choice = questdlg('Is the streak fully visible?', ...
                'Radius Check in Figure 15', ...
                'Yes','No, this image has no data','No, radii are not ok', 'No, radii are not ok');
            % Handle response
            switch choice
                case 'Yes'
                    check = check +1;
                    use = true;
                case 'No, this image has no data'
                    use = false;
                    break;
                case 'No, radii are not ok'
                    disp([choice 'Change the radius settings and rerun.'])
                    return;
            end
            
            
            
            if( use)
                % Find first and second maximum in intensity -> first =-HS second =+HS
                mv = max(intensity.(pid));
                
                pks = findpeaks(intensity.(pid));
                %Remove first max to find second.
                pks(find(pks == mv)) = [];
                if(isRV)
                    neghsind.(pid) = find(intensity.(pid) ==mv);
                    poshsind.(pid) = find(intensity.(pid) ==max(pks));
                else
                    poshsind.(pid) = find(intensity.(pid) ==mv);
                    neghsind.(pid) = find(intensity.(pid) ==max(pks));
                end
                
                %Create List with all intensities and hardstops.
                hardstops.(pid) = vertcat(hardstops.(pid), [poshsind.(pid), neghsind.(pid)]);
                intensities.(pid) = vertcat(intensities.(pid), intensity.(pid));
            end
        end
        
        
        ih1 = get(15,'Children');
        killme = findobj(prv,'type','text');
        delete(killme);
        prv = copyobj(allchild(otfhs2),otfhs1);
        cur = copyobj(allchild(ih1),otfhs2);
        title(otfhs2,sprintf('%s ontime=%dms',pid,ontimes(cc)));
        close 15;
        
        
        
        pause;
        cc = cc+1;
        
    end
end

%% Find the first successful streak
% for ps = [1:length(crm(:,1))]
%     pid = sprintf('pId%d',ps) ;
%     
%     % Assume that the final trial contains angles which are representative
%     % of the real hardstops
%     HS1f = hardstops.(pid)(end, 1);
%     HS2f = hardstops.(pid)(end, 2);
%     
%     % For each trial leading up to the last, check for the first image in
%     % which angles are within threshold of the real hardstops
%     for trial = 1:length(hardstops.(pid))
%         tHS1 = hardstops.(pid)(trial, 1);
%         tHS2 = hardstops.(pid)(trial, 2);
%         
%         if abs(tHS1-HS1f)<2 && abs(tHS2-HS2f)<2
%             ONTIMES.(pid) = ontimes{trial};
%             break;
%         end
%     end
% end


%
%     for ot = 1:8
% %     Criteria: Hs indices shouldnt change too much (more than 1)
%     Hs index 2 = hs index 1 + 5;
%     if(hardstops.(pid)(ot, 1) == hardstops.(pid)(ot, 2) - 5)
%
%     end
%     end
% end



imageMatrix = [];
bw_mine= [];
img = [];
save(horzcat(topdir,'workspace',stage,'.mat'));
% save(horzcat('C:\Users\sage\Desktop\Dropbox\PFS_EM\TEST_RESULTS\StreakResults\DailyBenchmarkResults/','workspace_',stage,date,'.mat'));



