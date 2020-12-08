import json
from pathlib import Path
import pytorch_lightning as pl
import torch

from package.data.tokenizers import RelationshipTokenizer
from package.data.label_encoders import LabelEncoder
from package.models import RelationshipEncoderLightningModule


def model_fn(model_dir):
    tokenizer = RelationshipTokenizer.from_file(
        file_path=Path(model_dir, 'tokenizer.json'),
        contains_entity_tokens=True
    )
    label_encoder = LabelEncoder.from_file(
        file_path=Path(model_dir, 'label_encoder.json')
    )
    model = RelationshipEncoderLightningModule.load_from_checkpoint(
        str(Path(model_dir, 'model.ckpt')),
        tokenizer=tokenizer,
        label_encoder=label_encoder
    )
    model.eval()
    print(model.model.linear.weight[:5, :5])
    print(model.model.text_encoder.encoder.layer[-1].output.dense.weight[:5, :5])
    
    model_assets = {
        'tokenizer': tokenizer,
        'label_encoder': label_encoder,
        'model': model
    }
    return model_assets


def input_fn(request_body_str, request_content_type):
    assert (
        request_content_type == "application/json"
    ), "content_type must be 'application/json'"
    request_body = json.loads(request_body_str)
    return request_body


def predict_fn(request, model_assets):
    encoding = model_assets['tokenizer'].encode(
        sequence=request['sequence'],
        entity_one_start=request['entity_one_start'],
        entity_one_end=request['entity_one_end'],
        entity_two_start=request['entity_two_start'],
        entity_two_end=request['entity_two_end']
    )

    token_ids = torch.tensor(encoding['ids']).unsqueeze(0)
    attention_mask = torch.tensor(encoding['attention_mask']).unsqueeze(0)
    logits = model_assets['model'](
        token_ids=token_ids,
        attention_mask=attention_mask
    )
    pred_pt = torch.argmax(logits, dim=1)
    pred_py = pred_pt[0].item()
    output = {
        'id': pred_py,
        'str': model_assets['label_encoder'].id_to_str(pred_py)
    }
    return output


def output_fn(prediction, response_content_type):
    assert (
        response_content_type == "application/json"
    ), "accept must be 'application/json'"
    response_body_str = json.dumps(prediction)
    return response_body_str
