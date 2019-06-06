#!/bin/bash

pushd build || exit 1

rm *.plist
zip -r theme.zip *
rm ../theme.zip
mv theme.zip ..

popd
