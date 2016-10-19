#!/bin/bash
#Parameters:
# AVG_File_Size File_Size_Distribution Arrival Gamma P_min P_max Beta Est_len PIT_lifetime Flow_control_timeout Test_duration Popularity Cat_name Client_id Start_time Client_Duration
#
# VERY IMPORTANT NOTES:
# * File_Size_Distribution is ignored at the moment. Only constant size is implemented
# * Arrival is in the same format as in the crackle config file (crackle.conf)
# * Test_duration is in seconds
# * Popularity is in the same format as in the crackle config file (crackle.conf)
# * Cat_name is the prefix of the catalog, to append in front of the object names.
#* PIT_lifetime is ignored
ENDFLAG="/tmp/ndnlocalclient"${14}"_stop"

FILESIZE=$1
FILESIZEDISTR=$2

# to lowercase
ARRIVAL=${3,,}

GAMMA=$4
PMIN=$5
DELTA_PMAX=$6
BETA=$7
ESTLEN=$8
PITLIFETIME=$9
FLOWCONTROLTIMEOUT=${10}

TESTDURATION=${11}
POPULARITY=${12}
CATALOG=${13}

CID=${14}

if [ -n "${15}" ]; then CLIENTSTARTTIME=${15}; else CLIENTSTARTTIME=0; fi
if [ -n "${16}" ]; then CLIENTDURATION=${16}; else CLIENTDURATION=$TESTDURATION; fi

rm -f $ENDFLAG

ARRIVAL_DIST=${ARRIVAL%%_*}
ARRIVAL_RATE=${ARRIVAL##*_}

echo "FS=$1 FS_DIST=$2 ARR=$3 GAMMA=$4 PMIN=$5 DELTA_PMAX=$6 BETA=$7 ESTLEN=$8 PITLT=$9 FLOW_TO=$FLOWCONTROLTIMEOUT"
echo "DURATION=$TESTDURATION CONTENT_POP=$POPULARITY CATALOG=$CATALOG CLIENT_ID=$CID CLIENTSTARTTIME=$CLIENTSTARTTIME"
echo "CLIENTDURATION=$CLIENTDURATION"

#declare -a pzipf
#pzipf[1]=$(echo "$zeta"|awk '{print 1/$PAR1}')


# alpha
##support=20000
zipfrandom(){
 echo $((RANDOM*32768+RANDOM)) |
   awk '{r=$1/(2^30);u=1-r*(1-(1/20000)^'$1');print int(1/(u^(1/'$1')))}';
}

# lambda
expovariate(){
 echo $((RANDOM*32768+RANDOM)) "$1" |
   awk '{u=$1/(2^30); print -log(u)/$2;}';
}


# lambda size
expotruncvariate(){
 echo $((RANDOM*32768+RANDOM)) "$1" "$2" |
   awk '{u=$1/(2^30); res= -log(u)/$2; res = res- int(res); print res*$3}';
}

#beta alpha high
weibulltruncvariate(){
 echo $((RANDOM*32768+RANDOM)) "$1" "$2" "$3" |
 awk '{F_high=1-exp(-($4/$3)^$2); u=1-$1/(2^30)*F_high; print $3 * (-log(u))^(1/$2)+1}';
# echo $(expotruncvariate "1.0" "1.0") "$1" "$2" |
#   awk '{print $3*($1)^(1/$2)}'; # return alpha * pow(expotruncvariate(1.0, 1.0), 1/beta)
}
    

#alpha
paretovariate(){
 echo $((RANDOM*32768+RANDOM)) "$1" |
   awk '{u=1-$1/(2^30);print 1/(u^(1/$2))+1}';
}

#alpha low high
paretotruncvariate(){
 echo $((RANDOM*32768+RANDOM)) "$1" "$2" "$3"|
   awk '{u=1-$1/(2^30)*(1-($3/$4)^$2);print $3/(u^(1/$2))}';
}

# tracefit uses a model inferred from a goodness of fit process 
# and us a piecewise model of three parts: head, waist and tail.
# head: truncated weibull
# waist: truncated zipf 
# tail: truncated weibull

# Parameters:x,alpha,C,th1,cons
CDF_waist()
{ echo "$1" "$2" "$3" "$4" "$5"|awk '{print $5+$3*($1^(1-$2)/(1-$2)-$4^(1-$2)/(1-$2))}'
}

#Parameters:y,alpha,C,th1,constant
reverse_CDF_waist()
{ echo "$1" "$2" "$3" "$4" "$5"|awk '{print ((($1-$5)/$3+$4^(1-$2)/(1-$2))*(1-$2))^(1/(1-$2))}'
}

#Parameters:x shape scale weight
pweibull()
{ echo "$1" "$2" "$3" "$4"|awk '{print (1-exp(-($1/$3)^$2))/$4}'
}

tracefit(){
# HTTP inferred parameters
 comment="
 th1=108
 th2=3951
 hshape=0.65
 hscale=70
 hweight=8
 walpha=0.863
 wweight=0.014
 tshape=0.25
 tscale=1800000
 tweight=1
 "
#Streaming inferred parameters
 th1=100
 th2=510
 hshape=0.5
 hscale=91
 hweight=2.9
 walpha=0.75
 wweight=0.026
 tshape=0.4
 tscale=1810
 tweight=1.1
# Youtube parameters
 comment="
 th1=50
 th2=225
 hshape=0.5
 hscale=31
 hweight=2.4
 walpha=0.61
 wweight=0.014
 tshape=0.5
 tscale=1425
 tweight=1.2
 "
 F1=$(pweibull $th1 $hshape $hscale $hweight)
 F2=$(CDF_waist $th2 $walpha $wweight $th1 $F1)
 Fth2=$(pweibull $th2 $tshape $tscale 1)
 FHigh=$(echo $Fth2 $F2 $tweight|awk '{print (1-$1+$2)/$3}')
 if awk "BEGIN {exit !($FHigh > 1)}"
 then
  FHigh=1
 fi
 
r=$(echo $((RANDOM*32768+RANDOM)) $FHigh|awk '{ print $1/(2^30)*$2}')
 if awk "BEGIN {exit !($r<=$F1)}" 
 then
   const=$(pweibull 1 $hshape $hscale $hweight)
   RANK=$(echo $r $const $hshape $hscale $hweight |awk '{print int($4*(-log((1-($1*$5+$2))))^(1/$3))}')
 elif awk "BEGIN {exit !($r<=$F2)}"
 then
   u=$(reverse_CDF_waist $r $walpha $wweight $th1 $F1)
   RANK=$(echo $u|awk '{print int($1)}')
 else
  RANK=$(echo $r $F2 $Fth2 $tshape $tscale $tweight |awk '{print int($5*(-log((1-(($1-$2)*$6+$3))))^(1/$4))}')
  fi
 echo $RANK
}

# dist, rate
interarrival(){
 case $1 in
   cbr) if [ $ARRIVAL_RATE == 0 ]; then awk 'BEGIN{print 0}'; else awk 'BEGIN{print 1/'"$ARRIVAL_RATE"'}';fi  ;;
   poisson) expovariate $ARRIVAL_RATE ;;
 esac
}

binarysearch()
{
  i=0
  array=($(echo "$@"))
  LowIndex=0
  HeighIndex=$((${#array[@]}-1))
  MidElement=-1
  while [ 1 -eq 1 ]
  do
    let i++
    if awk "BEGIN {exit !(($MidElement != $SearchedItem) && (($HeighIndex-$LowIndex) <= 1 ))}";then break;fi
    MidIndex=$(($LowIndex+($HeighIndex-$LowIndex)/2))
    MidElement=${array[$MidIndex]}
    if awk "BEGIN {exit !($MidElement == $SearchedItem)}"
    then
      LowIndex=$MidIndex
      HeighIndex=$MidIndex
    break
    elif awk "BEGIN {exit !($SearchedItem < $MidElement)}"
    then
      HeighIndex=$(($MidIndex))
    else
      LowIndex=$(($MidIndex))
    fi
  done
  echo $(($HeighIndex))
}

rzipf(){
  r=$(echo $((RANDOM*32768+RANDOM)) |awk '{ print $1/(2^30) }')
  SearchedItem=$r
  RANK=$(binarysearch "${pzipf[@]}")
  echo $RANK
} 

# 
#TEMPLATE: /OBJNUM0
filename(){
 POPDIST=${POPULARITY%%_*}
 PAR1=${POPULARITY#*_}
 PAR2=${PAR1#*_}
 PAR3=${PAR2#*_}
 
 PAR1=${PAR1%%_*}
 PAR2=${PAR2%%_*}
 PAR3=${PAR3%%_*}
 EXT=
 RANK=
 
# echo "D:$POPDIST p1:$PAR1 p2:$PAR2 p3:$PAR3"
 case ${POPDIST,,} in
 rzipf) RANK=($(rzipf)) ;; #Works correctly, without problems at rate=2 and N=10000
 zipf) RANK=$(paretotruncvariate $PAR1 1 $PAR2) ;; 
 weibull) RANK=$(weibulltruncvariate $PAR1 $PAR2 $PAR3) ;;
 geo) RANK=$(expotruncvariate $(awk 'BEGIN{print -log(1-'$PAR1')}') $PAR2); let "RANK++" ;; 
 trace) RANK=$(tracefit) ;;
 none) RANK=$PAR1;;
 esac
 
 echo "$CATALOGNAME/OBJNUM${CURRCATALOG}000$(printf '%d\n' ${RANK%%.*})$EXT"
}


#TODO: actual implementation
filesize(){
echo $FILESIZE
}

if [ ${POPULARITY%%_*} == rzipf ]; then
  PAR1=${POPULARITY#*_}
  PAR2=${PAR1#*_}
  PAR3=${PAR2#*_}
 
  PAR1=${PAR1%%_*}
  PAR2=${PAR2%%_*}
  PAR3=${PAR3%%_*}

  zeta=$(echo "$PAR1" "$PAR2"| awk '{for(i=1;i<=$2;i++){s+=i^-$1}} END{print s}')
  declare -a pzipf
  pzipf[1]=0
  pzipf[2]=$(echo "$zeta"|awk '{print 1/$PAR1}')
  
  for((i=1; i<$PAR2; i++)) do
    pzipf[$(($i+2))]=$(echo ${pzipf[$i+1]} "$i" "$PAR1" "$zeta"|awk '{print $1+(($2+1)^(-$3))/$4}')
  done 
fi

OLDIFS=$IFS
IFS="_" read -a PARAMS <<< "$CATALOG"

CATALOGNAME=${PARAMS[0]}
if [ ${PARAMS[1]} ]
then
        INTERVALCATALOG=${PARAMS[1]}
else
        INTERVALCATALOG=$CLIENTDURATION
fi
CURRCATALOG=0
IFS=$OLDIFS



#generate the catalog on a temporary file
REQUESTSLIST="/tmp/requestlist"${14}
rm -rf $REQUESTSLIST
touch $REQUESTSLIST

(
  let "CURRTIME=CLIENTSTARTTIME" #skip time if start time is not zero
  while [ 1 -eq 1 ]
  do
    if awk "BEGIN {exit !(($CURRTIME > $CLIENTDURATION)||($INTERVAL == 0)) }";then break;fi
    NAME=$(filename);
    INTERVAL=$(interarrival $ARRIVAL_DIST $ARRIVAL_RATE ); 
    CURRTIME=$(echo "$CURRTIME" "$INTERVAL"|awk '{print $1+$2}')
    if awk "BEGIN {exit !($CURRTIME > (($CURRCATALOG+1)*$INTERVALCATALOG)) }";then 
    let CURRCATALOG++
    fi
    echo $CURRTIME " " $INTERVAL " "  $NAME >> $REQUESTSLIST; 
  done
)&



#sleep for a while before start 
sleep 2


#sleep for the test duration than exit killing all active downloads and infinite sleep loop

fileasked=0
OLDTIME=0
(sleep ${TESTDURATION}; killall ndn-icp-download;) &
(sleep ${CLIENTDURATION}; touch $ENDFLAG;) & 

START=$(date +%s.%N)
echo $START
while [ ! -e $ENDFLAG ]; do
  if read -a REQUEST; 
  then 
    NEXTTIME=${REQUEST[0]}
    INTER=${REQUEST[1]}
    CONTENT=${REQUEST[2]}
    CONTENTSIZE=$(filesize)
    echo "$NEXTTIME" "$START" "$(date +%s.%N)" |awk '{interarrival= $1+$2-$3 ; if (interarrival>0) system("sleep "interarrival);else print "Intervals too close, no sleep"}'
    
    echo $(date +%s.%N)", * Starting download of content $CONTENT size $CONTENTSIZE chunks from host:client " $(hostname)
    (ndn-icp-download -n $CONTENTSIZE -g $GAMMA -m $PMIN -d $DELTA_PMAX -b $BETA -e $ESTLEN -t $FLOWCONTROLTIMEOUT "$CONTENT" | gawk '/transferred/{split($17, to, ":");print systime() ", Completed, '$CONTENT', " $13", " $15 ", " $10 ", '$(hostname)', '$CID', "  to[2], " $19", " $21";}/found:/{print systime () ", Failed , '$CONTENT', '$(hostname)', '$CID'"}')&
    if [ $ARRIVAL_RATE == 0 ]; then touch $ENDFLAG; fi  # return if # of files to transfer = 1i#  
  else
    echo "Too slow gneration process..."
  fi; 
done < $REQUESTSLIST
