#!/bin/bash

source env/bin/activate
python pack.py kenney.source

pushd build || exit 1

rm *.plist
zip -r theme.zip *
rm ../theme.zip
mv theme.zip ..

popd
