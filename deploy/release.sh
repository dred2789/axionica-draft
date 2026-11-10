#!/bin/sh
# Run on the server as the unprivileged deployment user.
set -eu
: "${DEPLOY_PATH:?Set DEPLOY_PATH}"
: "${DEPLOY_RELEASE:?Set DEPLOY_RELEASE}"
case "$DEPLOY_PATH" in /*) ;; *) exit 2 ;; esac
case "$DEPLOY_RELEASE" in incoming-*[!0-9-]*|incoming-|*[!a-z0-9-]*) exit 2 ;; incoming-[0-9]*-[0-9]*) ;; *) exit 2 ;; esac
cd "$DEPLOY_PATH"
# Serialize manual invocations as well as GitHub Actions.
exec 9>.deploy.lock
flock -x 9
previous=$(readlink current || true)
[ "$previous" != "$DEPLOY_RELEASE" ]
[ -d "$DEPLOY_RELEASE" ] && [ ! -L "$DEPLOY_RELEASE" ]
cleanup() {
    if [ "$(readlink current || true)" != "$DEPLOY_RELEASE" ]; then
        rm -rf -- "./$DEPLOY_RELEASE"
    fi
}
trap cleanup EXIT HUP INT TERM
tar -xzf "$DEPLOY_RELEASE/website.tar.gz" -C "$DEPLOY_RELEASE" --no-same-owner
rm "$DEPLOY_RELEASE/website.tar.gz"
test -s "$DEPLOY_RELEASE/ru/index.html"
test -s "$DEPLOY_RELEASE/en/index.html"
test -s "$DEPLOY_RELEASE/404.html"
find "$DEPLOY_RELEASE" -type d -exec chmod 755 {} +
find "$DEPLOY_RELEASE" -type f -exec chmod 644 {} +
ln -sfn "$DEPLOY_RELEASE" current.next
mv -Tf current.next current
# Kitchen policy: keep the live release only; failed uploads are also removed.
for old in incoming-*; do
    [ -d "$old" ] || continue
    [ "$old" = "$DEPLOY_RELEASE" ] || rm -rf -- "./$old"
done
printf 'Live release: %s\n' "$(readlink current)"
