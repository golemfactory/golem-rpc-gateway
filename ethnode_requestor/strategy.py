from yapapi.strategy import LeastExpensiveLinearPayuMS, SCORE_REJECTED


class BadNodeFilter(LeastExpensiveLinearPayuMS):
    bad_nodes = []

    @classmethod
    def blacklist_node(cls, node_address):
        cls.bad_nodes.append(node_address)

    async def score_offer(self, offer):
        node_address = offer.issuer

        if node_address in self.bad_nodes:
            return SCORE_REJECTED

        return await super().score_offer(offer)
