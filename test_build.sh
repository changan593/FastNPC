#!/bin/bash
cd /home/changan/MyProject/FastNPC/web/fastnpc-web
echo "Starting build at $(date)" > /tmp/build_output.txt
npm run build >> /tmp/build_output.txt 2>&1
BUILD_STATUS=$?
echo "Build finished at $(date) with status: $BUILD_STATUS" >> /tmp/build_output.txt
if [ -d "dist" ]; then
    echo "Dist directory exists" >> /tmp/build_output.txt
    ls -lh dist/ >> /tmp/build_output.txt
else
    echo "Dist directory NOT found" >> /tmp/build_output.txt
fi
echo "Build status: $BUILD_STATUS"
cat /tmp/build_output.txt

