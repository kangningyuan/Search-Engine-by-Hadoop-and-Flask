hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input /user/kangning/input.json \
    -output /user/kangning/output \
    -mapper 'python3 /home/kangning/search_engine/test4/mapper.py' \
    -reducer 'python3 /home/kangning/search_engine/test4/reducer.py' 

