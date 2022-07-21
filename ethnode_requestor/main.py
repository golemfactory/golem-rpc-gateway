import os
import asyncio
import colors
import requests
import time
from datetime import datetime, timezone, timedelta
from unittest import mock

from ya_activity.exceptions import ApiException
from yapapi.services import ServiceState
from yapapi import Golem

from proxy import EthnodeProxy
from service import Ethnode, EthnodePayload
from strategy import BadNodeFilter
from time_range import NodeRunningTimeRange
from utils import build_parser, print_env_info, run_golem_example

# the timeout after we commission our service instances
# before we abort this script
STARTING_TIMEOUT = timedelta(minutes=5)

# additional expiration margin to allow providers to take our offer,
# as providers typically won't take offers that expire sooner than 5 minutes in the future
EXPIRATION_MARGIN = timedelta(minutes=5)


RUNNING_TIME_DEFAULT = 316224000
NODE_RUNNING_TIME_DEFAULT = NodeRunningTimeRange("42000,84000")


ACTIVITY_STATE_TERMINATED = "Terminated"


def _instance_not_stopped(service: Ethnode) -> bool:
    return not service.stopped


async def main(
        service_name: str,
        num_instances: int,
        running_time: int,
        node_running_time_range: NodeRunningTimeRange,
        subnet_tag: str,
        payment_driver: str,
        payment_network: str,
        local_port: int,
):
    payload = EthnodePayload(runtime=service_name)

    async with Golem(
            budget=1.0,
            payment_driver=payment_driver,
            payment_network=payment_network,
            subnet_tag=subnet_tag,
            strategy=BadNodeFilter(),
    ) as golem:
        print_env_info(golem)
        expiration = (
                datetime.now(timezone.utc)
                + STARTING_TIMEOUT
                + EXPIRATION_MARGIN
                + timedelta(seconds=running_time)
        )
        proxy = EthnodeProxy(local_port, False)
        await proxy.run()

        print(colors.cyan(f"Local server listening on:\nhttp://localhost:{local_port}"))

        ethnode_cluster = await golem.run_service(
            Ethnode,
            payload=payload,
            num_instances=num_instances,
            instance_params=[
                {"node_running_time_range": node_running_time_range} for _ in range(num_instances)
            ],
            respawn_unstarted_instances=True,
            expiration=expiration,
        )

        proxy.set_cluster(ethnode_cluster)

        def available(cluster):
            return any(i.state == ServiceState.running for i in cluster.instances)

        def raise_exception_if_still_starting(cluster):
            if not available(cluster):
                raise Exception(
                    f"Failed to start {cluster} instances "
                    f"after {STARTING_TIMEOUT.total_seconds()} seconds"
                )

        commissioning_time = datetime.now()

        while (
                not available(ethnode_cluster)
                and datetime.now() < commissioning_time + STARTING_TIMEOUT
        ):
            print(ethnode_cluster.instances)
            await asyncio.sleep(5)

        raise_exception_if_still_starting(ethnode_cluster)

        print(colors.cyan("Eth nodes started..."))



        # wait until Ctrl-C

        while datetime.now(timezone.utc) < expiration:
            costs = {}
            state = {}

            for i in filter(lambda _i: _i._ctx, ethnode_cluster.instances):
                try:
                    costs[str(i)] = await i._ctx.get_cost()
                    s = (await i._ctx.get_raw_state()).to_dict().get("state", [None, None])[0]
                    state[str(i)] = s
                    if s == ACTIVITY_STATE_TERMINATED:
                        # restart if the activity state suggests a provider's end termination
                        i.fail(blacklist_node=False)
                except ApiException:
                    # terminate the agreement and restart the node after a costs check fails
                    i.fail(blacklist_node=False)
                    costs[str(i)] = None
                    state[str(i)] = None
                except AttributeError:
                    # just ignore the error - the instance is most likely being restarted
                    pass

            print(ethnode_cluster.instances)
            print(colors.cyan(costs))
            print(colors.magenta(state))

            try:
                await asyncio.sleep(10)
            except (KeyboardInterrupt, asyncio.CancelledError):
                break

        print(colors.cyan("Stopping..."))
        # signal the instances not to restart

        await proxy.stop()

        for instance in ethnode_cluster.instances:
            instance.stop()

        ethnode_cluster.stop()


async def main_no_proxy(args):
    print(colors.yellow(f"Warning - running in proxy only mode. This is not proper way of running the service. Use for development."))
    proxy = EthnodeProxy(None, args.local_port, True)
    await proxy.run()

    print(colors.cyan(f"Local server listening on:\nhttp://localhost:{args.local_port}"))
    while True:
        await asyncio.sleep(100)


if __name__ == "__main__":
    parser = build_parser("Ethnode requestor")
    parser.add_argument(
        "--service",
        type=str,
        help="Service name",
        choices=("bor-service", "geth-service"),
        default="bor-service",
    )
    parser.add_argument(
        "--num-instances",
        type=int,
        default=1,
        help="Number of initial instances/users to create",
    )
    parser.add_argument(
        "--running-time",
        default=316224000,
        type=int,
        help=("Service expiry time " "(in seconds, default: %(default)s)"),
    )
    parser.add_argument(
        "--proxy-only",
        default=False,
        type=bool,
        help=("In proxy only mode run only proxy and ignore requestor part"),
    )
    parser.add_argument(
        "--check-for-yagna",
        default=False,
        type=bool,
        help=("Check for yagna if docker enabled"),
    )
    parser.add_argument(
        "--node-running-time",
        default=str(NODE_RUNNING_TIME_DEFAULT),
        type=NodeRunningTimeRange,
        help=(
            "The running time range [min,max] of a single instance "
            "(in seconds, default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--local-port", default=8545, type=int, help="The port the proxy is listening on."
    )

    # set_yagna_app_key_to_env("yagna");

    # payment_init_command = f"yagna payment init --sender"
    # print(f"Running command: {payment_init_command}")
    # payment_init = subprocess.Popen(payment_init_command, shell=True)
    # payment_init.communicate()

    now = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")

    parser.set_defaults(log_file=f"eth-request-{now}.log")
    args = parser.parse_args()
    if args.check_for_yagna:
        max_tries = 15
        for tries in range(0, max_tries):
            try:
                time.sleep(1.0)
                print("Checking for yagna if docker started")
                url = os.getenv("YAGNA_MONITOR_URL") or 'http://127.0.0.1:3333'
                resp = requests.get(url=url)
                data = resp.json()
                if data["payment_initialized"]:
                    print("Yagna detected, continuing...")
                    break
                else:
                    raise Exception("yagna in docker not initialized")
            except Exception as ex:
                print("Check for yagna startup failed: " + str(ex))
                continue



    print(colors.green(f"Patching yapapi - TODO remove in future version of yapapi"))

    patch = mock.patch(
        "yapapi.services.Cluster._instance_not_started",
        staticmethod(_instance_not_stopped),
    )
    patch.start()



    if args.proxy_only:
        run_golem_example(
            main_no_proxy(args),
            log_file=args.log_file,
        )
    else:
        run_golem_example(
            main(
                service_name=args.service,
                num_instances=args.num_instances,
                running_time=args.running_time,
                node_running_time_range=args.node_running_time,
                subnet_tag=args.subnet_tag,
                payment_driver=args.payment_driver,
                payment_network=args.payment_network,
                local_port=args.local_port,
            ),
            log_file=args.log_file,
        )
