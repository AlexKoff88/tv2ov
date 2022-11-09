from lib2to3.pytree import convert
import sys
import os

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import torchvision.models as models

import torchvision.datasets as datasets
import torchvision.transforms as transforms

from openvino.runtime import Core
import openvino.runtime as ov

from tv2ov.converter import PreprocessorConvertor

MODEL_LOCAL_PATH="mobilenet_v2.onnx"
OUTPUT_MODEL="mobilenet_v2_preprocess.xml"

def get_onnx_model(model):
    dummy_input = torch.randn(1, 3, 224, 224)
    input_names = ["input"] 
    output_names = ["output1"]
    torch.onnx.export(model, dummy_input, MODEL_LOCAL_PATH, verbose=True, input_names=input_names, output_names=output_names)

normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                    std=[0.229, 0.224, 0.225])
transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        normalize,
    ])

torch_model = models.mobilenet_v2(pretrained=True) 
torch_model.eval()

get_onnx_model(torch_model)
core = Core()
model = core.read_model(model=MODEL_LOCAL_PATH)

## Embed preprocessing into OV model
convertor = PreprocessorConvertor(model)
model = convertor.from_torchvision(0, transform, [1,3,-1,-1])

ov.serialize(model, OUTPUT_MODEL, OUTPUT_MODEL.replace(".xml", ".bin"))

## Test inference
test_input = np.random.randint(255, size=(1, 3, 480, 640), dtype=np.uint8)
'''dataset = datasets.FakeData(size=10, 
                    image_size=(3,480,640), 
                    num_classes=1000) 

data_loader = torch.utils.data.DataLoader(
        dataset, batch_size=1, num_workers=1, shuffle=False)'''
test_image = Image.fromarray(test_input)
transformed_input = transform(test_image)

torch_result = torch_model(transformed_input).numpy()
ov_result = model(test_input)

result = np.max(np.absolute(torch_result - ov_result))
print(f"Max abs diff: {result}")