from pynq import Overlay, allocate
import numpy as np
import pandas as pd

class predict_model():

    def dataAggregator(self, segmentedDataDf): #Aggregate the raw data before feeding to prediction
        aggregatedData = {}
        for col in segmentedDataDf.columns:  
            aggregatedData[f'{col}Min'] = segmentedDataDf[col].min()
            aggregatedData[f'{col}Max'] = segmentedDataDf[col].max()
            aggregatedData[f'{col}Mean'] = segmentedDataDf[col].mean()
            aggregatedData[f'{col}Std'] = segmentedDataDf[col].std()
        aggregatedDataDf = pd.DataFrame(aggregatedData)
        return aggregatedDataDf
    
    def __init__(self, overlay):
        self.N_FEATURES = 24
        self.N_ACTIONS = 8
        self.input_buffer = allocate(shape=(self.N_FEATURES,), dtype=np.float32)
        self.output_buffer = allocate(shape=(self.N_ACTIONS,), dtype=np.float32)

    def send(self, input_data):
        self.N_FEATURES = 24
        for i in range(self.N_FEATURES):
            self.input_buffer[i] = input_data[i]
        self.dma.sendchannel.transfer(self.input_buffer)
        self.dma.recvchannel.transfer(self.output_buffer)
        self.dma.recvchannel.wait()
        self.dma.sendchannel.wait()
        return self.output_buffer
    
    def predict(self, input_data):
        self.send(input_data)
        results = []
        self.N_ACTIONS = 8
        for i in range(self.N_ACTIONS):
            results.append(self.output_buffer[i])
        return results

    def free_buffer(self):
        self.input_buffer.freebuffer()
        self.output_buffer.freebuffer()

    def get_action(self, data):
        #bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
        #overlay = Overlay(bitstream_path)
        #predictor = predict_model(overlay)
        data = self.dataAggregator(data) #this would already have flattened it out
        predict_results = self.predict(data)
        prediction = np.argmax(predict_results) + 1
        self.free_buffer()
        return prediction
