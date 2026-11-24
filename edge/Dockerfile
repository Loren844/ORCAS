FROM rust:1.90-slim-bookworm AS build

WORKDIR /src

# Dépendances compilées dans une couche à part, réutilisée tant que Cargo.lock ne change pas.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs \
    && cargo build --release --locked \
    && rm -rf src target/release/deps/orca_edge* target/release/orca-edge

COPY src ./src
RUN cargo build --release --locked

FROM debian:bookworm-slim

RUN useradd --system --uid 1000 orca
COPY --from=build /src/target/release/orca-edge /usr/local/bin/orca-edge
USER orca

ENTRYPOINT ["orca-edge"]
