import os
from tqdm import tqdm

import utils
from setup import Config
from logger import logger

from typing import Optional, List
import torch
from torch.utils.data import DataLoader
import torch.nn as nn
from vae_model import Db_vae
from dataset import *
from dataclasses import asdict

class Evaluator:
    """
    Class that evaluates a model based on a given pre-initialized model or path_to_model
    and displays several performance metrics.
    """
    def __init__(
        self,
        path_to_eval_dataset,
        z_dim: int,
        batch_size: int,
        device: str,
        nr_windows: int,
        stride: float,
        model_name: str,
        path_to_model: Optional[str] = None,
        model: Optional[Db_vae] = None,
        config: Optional[Config] = None,
        **kwargs
    ):
        self.z_dim = z_dim
        self.device = device
        self.batch_size = batch_size
        self.model_name = model_name
        self.nr_windows = nr_windows
        self.stride = stride

        self.config = config

        self.path_to_model = path_to_model
        self.model: Db_vae = self.init_model(path_to_model, model)
        self.path_to_eval_dataset = path_to_eval_dataset
        _, _, df_test, _ = get_df()
        self.csv = df_test

    def init_model(self, path_to_model: Optional[str] = None, model: Optional[Db_vae] = None):
        """Initializes a stored model or one that directly comes from training."""
        if model is not None:
            logger.info("Using model passed")
            return model.to(self.device)

        # If path_to_model, load model from file
        if path_to_model:
            return Db_vae.init(path_to_model, self.device, self.z_dim).to(self.device)

        logger.error(
            "No model or path_to_model given",
            next_step="Evaluation will not run",
            tip="Instantiate with a trained model, or set `path_to_model`."
        )
        raise Exception

    def eval(self, filter_skin_color = 5, max_images: int = -1):
        """Evaluates a model based and returns the amount of correctly classified and total classified images."""
        self.model.eval()
        #
        # if dataset_type == "":
        eval_loader: DataLoader = make_eval_loader(
            csv=self.csv,
            filter_skin_color=filter_skin_color,
            **asdict(self.config)
        )
        # else:
        #     params = {**asdict(self.config), 'max_images': max_images}
        #
        #     eval_loader: DataLoader = make_eval_loader(
        #         filter_skin_color=filter_skin_color,
        #         filter_exclude_gender=filter_exclude_gender,
        #         dataset_type=dataset_type,
        #         **params
        #     )

        correct_count, count, LABELS, SIGOUTS  = self.eval_model(eval_loader)
        return correct_count, count, LABELS, SIGOUTS

    def eval_on_setups(self, eval_name: Optional[str] = None):
        """Evaluates a model and writes the results to a given file name."""
        eval_name = self.config.eval_name if eval_name is None else eval_name

        # Define the predefined setups
        # gender_list = [["Female"], ["Male"], ["Female"], ["Male"]]
        skin_list = [0, 1, 2, 3, 4, 5]
        name_list = ["type_1", "type_2", "type_3", "type_4", "type 5", "type 6"]

        # Init the metrics
        accuracies = []
        aucs = []
        sensitivities = []
        specificities = []
        correct = 0
        total_count = 0

        # Go through the predefined setup
        for i in range(6):
            logger.info(f"Running setup for {name_list[i]}")

            # Calculate on the current setup
            correct_count, count, LABELS, SIGOUTS = self.eval(
                filter_skin_color=skin_list[i]
            )

            # Calculate the metrics
            a_u_c = utils.calculate_AUC(LABELS, SIGOUTS)

            # sensitivity, specificity = utils.calculate_sens_spec(LABELS,SIGOUTS)


            accuracy = correct_count / count * 100
            correct += correct_count
            total_count += count

            # Log the recall
            logger.info(f"Accuracy for {name_list[i]} is {accuracy:.3f}")
            logger.info(f"AUC for {name_list[i]} is {a_u_c:.3f}")
            accuracies.append(accuracy)
            aucs.append(a_u_c)
            # sensitivities.append(sensitivity)
            # specificities.append(specificity)

        # Calculate the average recall
        avg_acc = correct/total_count*100
        avg_auc = sum(aucs)/len(name_list)
        # avg_sens = sum(sensitivities) / len(name_list)
        # avg_spec = sum(specificities) / len(name_list)

        acc_variance = (torch.tensor(accuracies)).var().item()
        auc_variance = (torch.tensor(aucs)).var().item()

        # # Calculate the amount of negative performance
        # logger.info("Evaluating on negative samples")
        # incorrect_neg, neg_count = self.eval(max_images=1270)
        # correct_neg: int = neg_count - incorrect_neg
        #
        # # Calculate the precision and accuracy
        # precision = correct_pos/(correct_pos + neg_count)*100
        # accuracy = (correct_pos + correct_neg)/(2*1270)*100

        # Logger info
        logger.info(f"Accuracy => all: {avg_acc:.3f}")
        logger.info(f"Accuracy => type 1: {accuracies[0]:.3f}")
        logger.info(f"Accuracy => type 2: {accuracies[1]:.3f}")
        logger.info(f"Accuracy => type 3: {accuracies[2]:.3f}")
        logger.info(f"Accuracy => type 4: {accuracies[3]:.3f}")
        logger.info(f"Accuracy => type 5: {accuracies[4]:.3f}")
        logger.info(f"Accuracy => type 6: {accuracies[5]:.3f}")
        logger.info(f"Accuracy Variance => {acc_variance:.3f}")
        logger.info(f"AUC => all: {avg_auc:.3f}")
        logger.info(f"AUC => type 1: {aucs[0]:.3f}")
        logger.info(f"AUC => type 2: {aucs[1]:.3f}")
        logger.info(f"AUC => type 3: {aucs[2]:.3f}")
        logger.info(f"AUC => type 4: {aucs[3]:.3f}")
        logger.info(f"AUC => type 5: {aucs[4]:.3f}")
        logger.info(f"AUC => type 6: {aucs[5]:.3f}")
        logger.info(f"AUC Variance => {auc_variance:.3f}")
        # logger.info(f"Sensitivity => all: {avg_sens:.3f}")
        # logger.info(f"Sensitivity => type 1: {sensitivities[0]:.3f}")
        # logger.info(f"Sensitivity => type 2: {sensitivities[1]:.3f}")
        # logger.info(f"Sensitivity => type 3: {sensitivities[2]:.3f}")
        # logger.info(f"Sensitivity => type 4: {sensitivities[3]:.3f}")
        # logger.info(f"Sensitivity => type 5: {sensitivities[4]:.3f}")
        # logger.info(f"Sensitivity => type 6: {sensitivities[5]:.3f}")
        # logger.info(f"Specificity => all: {avg_spec:.3f}")
        # logger.info(f"Specificity => type 1: {specificities[0]:.3f}")
        # logger.info(f"Specificity => type 2: {specificities[1]:.3f}")
        # logger.info(f"Specificity => type 3: {specificities[2]:.3f}")
        # logger.info(f"Specificity => type 4: {specificities[3]:.3f}")
        # logger.info(f"Specificity => type 5: {specificities[4]:.3f}")
        # logger.info(f"Specificity => type 6: {specificities[5]:.3f}")
        # logger.info(f"Recall => white male: {recalls[2]:.3f}")
        # logger.info(f"Recall => white female: {recalls[3]:.3f}")

        # logger.info(f"Precision => {precision:.3f}")

        # Write final results
        path_to_eval_results = f"results/logs/{self.config.test_no}/results.txt"
        with open(path_to_eval_results, 'a+') as write_file:

            # If file has no header
            if not os.path.exists(path_to_eval_results) or os.path.getsize(path_to_eval_results) == 0:
                write_file.write(f"name,dark male,dark female,light male,light female,var,precision,recall,accuracy\n")

            write_file.write(f"{self.path_to_model}_{self.model_name}")
            write_file.write(f",{accuracies[0]:.3f},{accuracies[1]:.3f},{accuracies[2]:.3f},{accuracies[3]:.3f},"
                             f"{accuracies[4]:.3f},{accuracies[5]:.3f},avg_acc:{avg_acc:.3f},acc_variance:{acc_variance:.3f},"
                             f"{aucs[0]:.3f},{aucs[1]:.3f},{aucs[2]:.3f},{aucs[3]:.3f},{aucs[4]:.3f},{aucs[5]:.3f},"
                             f"avg_auc:{avg_auc:.3f},auc_variance:{auc_variance:.3f}\n")

        logger.success("Finished evaluation!")

    def eval_model(self, eval_loader: DataLoader):
        """Perform evaluation of a single epoch."""
        self.model.eval()

        count = 0
        correct_count = 0
        SIGOUTS = []
        LABELS = []

        bar = tqdm(eval_loader)
        # Iterate over all images and their sub_images
        for _, batch in enumerate(bar):
            count += 1
            data, labels, _ , _ = batch

            for images, target in zip(data, labels):
                # images = images.cpu()
                # images = target.cpu()
                if len(images.shape) == 5:
                    images = images.squeeze(dim=0)

                images = images.unsqueeze(dim=0)

                images = images.to(self.device)

                pred, sigout = self.model.forward_eval(images)

                pred = pred.detach().cpu()

                if (pred > 0 and target==1) | (pred < 0 and target==0):
                    correct_count += 1
                    break

                SIGOUTS.append(sigout.detach().cpu())
                LABELS.append(target)

        LABELS = torch.stack(LABELS).numpy()
        SIGOUTS = torch.cat(SIGOUTS).numpy()

        logger.info(f"Amount of labels:{count}, Correct labels:{correct_count}")

        return correct_count, count, LABELS, SIGOUTS
