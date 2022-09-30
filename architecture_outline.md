```mermaid

graph LR
    classDef external color:#888, fill: white, stroke: #ccc;
    classDef externalChild color:#444, fill: #eee, stroke: #ccc, padding: 10px;
    
    classDef golem color:#446, fill:#e6eeff, stroke: #ccd;
    
    classDef requestorNode color:#400, fill:#ffd, stroke: #aab;
    classDef requestorComponent color:#600, fill:#fea, stroke: #aab;
    classDef requestorChild color:#000, fill:#da0, stroke: #aab;

    classDef providerNode color:#040, fill:#efd, stroke: #aab;
    classDef providerComponent color:#260, fill:#dea, stroke: #aab;
    classDef providerChild color:#000, fill:#ad0, stroke: #aab;
    
    subgraph reality["Reality NFT platform"]
        client(Reality NFT client):::externalChild
    end
    reality:::external
    client...->rproxy
    subgraph golem[Golem Network]
        subgraph golemreq[Golem RPC Gateway]
            subgraph ragent[Requestor agent]
                rproxy(HTTP proxy):::requestorChild
            end
            rproxy.->rdaemon
            rdaemon(Yagna daemon):::requestorChild
        end
        golemreq:::requestorNode
        ragent:::requestorComponent;
        rdaemon.->pdeamon1
        rdaemon.->pdeamon2
        rdaemon.->pdeamon3
        subgraph golemprovA[Provider A]
            pdeamon1(Yagna daemon):::providerChild
            pdeamon1.->ethnode1
            subgraph pagentA[Provider agent]
                ethnode1("Ethereum node"):::providerChild
            end
        end
        subgraph golemprovB[Provider B]
            pdeamon2(Yagna daemon):::providerChild
            pdeamon2.->ethnode2
            subgraph pagentB[Provider agent]
                ethnode2("Ethereum node"):::providerChild
            end
        end
        subgraph golemprovC[Provider C]
            pdeamon3(Yagna daemon):::providerChild
            pdeamon3.->ethnode3
            subgraph pagentC[Provider agent]
                ethnode3("Ethereum node"):::providerChild
            end
        end
        golemprovA:::providerNode
        golemprovB:::providerNode
        golemprovC:::providerNode
        pagentA:::providerComponent
        pagentB:::providerComponent
        pagentC:::providerComponent
    end
    golem:::golem
    ethnode1...->blockchain
    ethnode2...->blockchain
    ethnode3...->blockchain
    subgraph eth[Ethereum network]
        blockchain(Ethereum/Polygon blockchain):::externalChild
    end
    eth:::external

```