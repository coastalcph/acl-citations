#!/usr/bin/fish

cd ..
touch /run/media/bollmann/Intenso/anthology
python ./acl_anthology.py fetch 'P1?-1*' 'P1?-2*' 'J1*' 'E1?-*' 'E17-2*' 'E14-4*' 'D1?-1*' 'N1?-1*' 'N18-2*' 'Q1*' --destination /run/media/bollmann/Intenso/anthology/

for d in /run/media/bollmann/Intenso/anthology/*
         echo "Calling GROBID client on $d"
         mkdir /run/media/bollmann/Intenso/anthology-tei/(basename "$d")
         python /home/bollmann/repositories/grobid-client-python/grobid-client.py --input "$d" --output /run/media/bollmann/Intenso/anthology-tei/(basename "$d") --config config.json --n 4 processReferences >> acl_2010andnewer.log 2>&1
end

python ./parse_tei.py /run/media/bollmann/Intenso/anthology-tei/?1* --csv acl-2010andnewer.csv

echo "Files left out due to GROBID errors:" (grep "error 500" acl_2010andnewer.log -c)
