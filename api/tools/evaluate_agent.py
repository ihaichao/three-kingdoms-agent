import argparse

from three_kingdoms.application.evaluation.evaluate import evaluate_agent

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--nb-samples",
        type=int,
        default=None,
        help="只跑前 N 条，用来小批量试跑。不传则跑全量。",
    )
    args = parser.parse_args()
    evaluate_agent(nb_samples=args.nb_samples)
