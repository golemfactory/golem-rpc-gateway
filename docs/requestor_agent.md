```mermaid

graph LR
    classDef external color:white, fill: white, stroke: white;
    classDef externalChild color:#888, fill: white, stroke: #ccc;

    classDef requestorNode color:#400, fill:#ffd, stroke: #aab;
    classDef requestorComponent color:#600, fill:#fffabf, stroke: #aab;
    classDef requestorComponent2 color:#400, fill:#fea, stroke: #aab;
    classDef requestorChild color:#000, fill:#da0, stroke: #aab;
    linkStyle default stroke: #aaa, fill: none;

    subgraph clients[" "]
        client(Reality NFT client)
        client:::externalChild
        operator(GolemFactory administrator)
        operator:::externalChild
    end

    client---->rproxy
    operator.->yagna_mon
    operator.->rhttp
    clients:::external

    subgraph golemreq[Golem RPC Gateway]
        subgraph ragent[Requestor agent]
            subgraph rhttpserver[ Requestor HTTP Server ]
                rhttp(Agent monitor REST API):::requestorChild
                rproxy(RPC proxy):::requestorChild
            end
            yapapi(yapapi requestor):::requestorChild
            db(DB back-end):::requestorChild
            yapapi.->rproxy
            rhttp.->yapapi
            yapapi.->db
            rproxy.->db
        end
        rhttpserver:::requestorComponent2
        subgraph rdaemon[Requestor daemon]
            ryagna(Yagna daemon):::requestorChild
            yagna_mon(Yagna monitor REST API):::requestorChild
            yagna_mon.->ryagna
        end
        yapapi...->ryagna
    end
    golemreq:::requestorNode
    ragent:::requestorComponent;
    rdaemon:::requestorComponent;

    provider1(Provider)
    provider2(Provider)
    provider3(Provider)

    rproxy-->provider1
    rproxy-->provider2
    rproxy-->provider3
    ryagna.->provider1
    ryagna.->provider2
    ryagna.->provider3
    provider1:::externalChild
    provider2:::externalChild
    provider3:::externalChild

```