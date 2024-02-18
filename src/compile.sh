prog="bildverkleinerer"
win="${prog}_win"
win_exec="${prog}.exe"
lin="${prog}_lin"
lin_exec="${prog}.bin"
pyinstaller_opts="--noupx --noconsole"
date=$(head -n 1 $prog.py)
sed -i "1 s/.*//" $prog.py
# if [ -z $1 ]; then
#     check_update() {
#         ret=1
#         for fn in *.py; do
#             a=($(sha256sum $fn))
#             if [ -f $fn.sha256sum ]; then
#                 b=$(cat $fn.sha256sum)
#                 if [[ "$a" != "$b" ]]; then
#                     ret=0
#                     echo $fn
#                     echo "$a" >$fn.sha256sum
#                 fi
#             else
#                 echo "$a" >$fn.sha256sum
#                 ret=0
#             fi
#         done
#         return $ret
#     }
#     check_update
#     ret=$?
#     if [ $ret == 1 ]; then
#         echo "no updates"
#         sed -i "1 s/.*/$date/" $prog.py
#         exit 1
#     fi
# fi

git diff 
exit 1

printf -v date '%(%Y-%m-%d %H:%M:%S)T' -1
date="build_date=\"$date\""
echo $date
sed -i.bak "1 s/.*/$date/" $prog.py

wine C:/Python38/python.exe -m pip install -r requirements.txt
wine C:/Python38/Scripts/pyinstaller.exe $pyinstaller_opts $prog.py --hidden-import='PIL._tkinter_finder'
tar cf - dist/$prog/* | xz -4e >dist/${win}.tar.xz
sha256=($(sha256sum dist/${prog}/${win_exec}))
echo -n "$sha256" >dist/${win_exec}.sha256
rm -r dist/$prog

pyinstaller $pyinstaller_opts $prog.py --hidden-import='PIL._tkinter_finder'
mv dist/$prog/$prog dist/$prog/$lin_exec
tar cf - dist/$prog/* | xz -4e >dist/${lin}.tar.xz
sha256=($(sha256sum dist/${prog}/${lin_exec}))
echo -n "$sha256" >dist/${lin_exec}.sha256
rm -r dist/$prog

push_update() {
    cd links
    tag=$(head -n 1 tag.txt)
    tag="$(($tag + 1))"
    echo $tag >tag.txt
    git commit -am "v$tag" && git push
    gh release create v$tag -F changelog.md ../dist/$prog*
    echo "v$tag"
    gh release delete v$(($tag - 1)) --yes
    git push --delete origin v$(($tag - 1))
    cd ..
}

push_update

rm dist/$prog*
