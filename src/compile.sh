prog="bildverkleinerer"
win="${prog}_win"
win_exec="${prog}.exe"
lin="${prog}_lin"
lin_exec="${prog}.bin"
scriptdir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ ! $scriptdir == $PWD ]; then 
    cd $scriptdir
    echo "-> cd $scriptdir" 
fi 
distpath="$scriptdir/../dist"
buildpath="$scriptdir/../build"
specpath="$scriptdir/../spec"
pyinstaller_opts="--noupx --noconsole --specpath $specpath --distpath $distpath --workpath $buildpath" 
date=$(head -n 1 $prog.py)
sed -i "1 s/.*//" $prog.py

if [[ ! `git status --porcelain` ]]; then
    echo "no change"
    exit 1 
fi

check_update() {
    ret=1
    for fn in *.py; do
        a=($(sha256sum $fn))
        if [ -f $fn.sha256sum ]; then
            b=$(cat $fn.sha256sum)
            if [[ "$a" != "$b" ]]; then
                ret=0
                echo $fn
                echo "$a" >$fn.sha256sum
            fi
        else
            echo "$a" >$fn.sha256sum
            ret=0
        fi
    done
    return $ret
}
check_update
ret=$?
if [ $ret == 1 ]; then
    echo "no .py updates"
    sed -i "1 s/.*/$date/" $prog.py
    git commit -am "upity" && git push 
    exit 1
fi

printf -v date '%(%Y-%m-%d %H:%M:%S)T' -1
date="build_date=\"$date\""
echo $date
sed -i.bak "1 s/.*/$date/" $prog.py
git commit -am "$date" && git push 

wine C:/Python38/python.exe -m pip install -r requirements.txt
wine C:/Python38/Scripts/pyinstaller.exe $pyinstaller_opts $prog.py --hidden-import='PIL._tkinter_finder'
tar cf - $distpath/$prog/* | xz -4e >$distpath/${win}.tar.xz
sha256=($(sha256sum $distpath/${prog}/${win_exec}))
echo -n "$sha256" >$distpath/${win_exec}.sha256
rm -r $distpath/$prog

pyinstaller $pyinstaller_opts $prog.py --hidden-import='PIL._tkinter_finder'
mv $distpath/$prog/$prog $distpath/$prog/$lin_exec
tar cf - $distpath/$prog/* | xz -4e >$distpath/${lin}.tar.xz
sha256=($(sha256sum $distpath/${prog}/${lin_exec}))
echo -n "$sha256" >$distpath/${lin_exec}.sha256
rm -r $distpath/$prog

push_update() {
    tag=$(head -n 1 tag.txt)
    tag="$(($tag + 1))"
    echo $tag >tag.txt
    git commit -am "v$tag" && git push
    gh release create v$tag -F changelog.md $distpath/$prog*
    echo "v$tag"
    gh release delete v$(($tag - 1)) --yes
    git push --delete origin v$(($tag - 1))
}

cd .. 
push_update

rm $distpath/$prog*
