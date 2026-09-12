repo := "ghcr.io/yayuniversal/immich-folder-albums"

# build the docker image (single-arch)
build tag="latest":
	docker buildx build \
		--tag {{repo}}:{{tag}} .

# build and push the multi-arch manifest list
push tag="latest":
	docker buildx build \
		--provenance=false \
		--platform linux/amd64,linux/arm64 \
		--tag {{repo}}:{{tag}} --tag {{repo}}:latest --push .

# build, push, and tag the release in git
release tag: (push tag)
	git tag {{tag}}
	git push origin {{tag}}
