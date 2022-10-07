```mermaid

graph LR
    classDef external color:#444, fill: white, stroke: white;
    classDef externalChild color:#888, fill: white, stroke: #ccc;

    classDef providerNode color:#040, fill:#efd, stroke: #aab;
    classDef providerComponent color:#260, fill:#dea, stroke: #aab;
    classDef providerComponent2 color:#150, fill:#d0e0a0, stroke: #aab;
    classDef providerChild color:#000, fill:#ad0, stroke: #aab;

    linkStyle default stroke: #aaa, fill: none;

    subgraph requestor[Requestor]
        rpcproxy(Requestor's RPC proxy)
        rpcproxy:::externalChild
        rdaemon(Requestor's yagna daemon)
        rdaemon:::externalChild
    end

    rpcproxy------>pnode
    rdaemon.->pdaemon
    requestor:::external

    subgraph golemprov[Golem Provider]
        subgraph pagent[Provider agent]
            pnode(Ethereum node):::providerChild
            phttp-runtime(HTTP runtime):::providerChild
        end
        pdaemon(Yagna daemon):::providerChild
        pdaemon...->phttp-runtime
        phttp-runtime.->pnode
    end
    pagent:::providerComponent2;
    golemprov:::providerComponent

    pnode-->ethereum(Ethereum network)
    ethereum:::externalChild

```