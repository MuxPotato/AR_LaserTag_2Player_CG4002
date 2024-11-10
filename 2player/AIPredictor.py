from pynq import Overlay, allocate
import numpy as np
import pandas as pd
#import joblib
#import torch 

class Predictor():

    def dataAggregator(self, segmentedDataDf): #Aggregate the raw data before feeding to prediction
        aggregatedData = {}
        for col in segmentedDataDf.columns:  
            aggregatedData[f'{col}Min'] = [segmentedDataDf[col].min()]
            aggregatedData[f'{col}Max'] = [segmentedDataDf[col].max()]
            aggregatedData[f'{col}Mean'] = [segmentedDataDf[col].mean()]
            aggregatedData[f'{col}Std'] = [segmentedDataDf[col].std()]
        aggregatedDataDf = pd.DataFrame(aggregatedData)
        return aggregatedDataDf
    
    def __init__(self, overlay):
        self.overlay = overlay  
        self.dma = self.overlay.axi_dma_0

    def send(self, input_data):
        self.N_FEATURES = 24
        #input_array = input_data.to_numpy().flatten()
        input_array = input_data.flatten()
        for i in range(self.N_FEATURES):
            self.input_buffer[i] = input_array[i]
        self.dma.sendchannel.transfer(self.input_buffer)
        self.dma.recvchannel.transfer(self.output_buffer)
        self.dma.recvchannel.wait()
        self.dma.sendchannel.wait()
        return self.output_buffer
    
    def predict(self, input_data):
        self.send(input_data)
        results = []
        self.N_ACTIONS = 7
        for i in range(self.N_ACTIONS):
            results.append(self.output_buffer[i])
        return results

    def free_buffer(self):
        self.input_buffer.freebuffer()
        self.output_buffer.freebuffer()

    def get_action(self, data):
        training_means = np.array(
        [-1.92297905e+00, 1.16659911e+00, -2.99873461e-01, 7.89662769e-01,
        -1.58190887e+00, 1.08269523e+00, -3.14215645e-01, 4.67901155e-01,
        -1.52494504e+00, 1.33373967e+00, -7.87930668e-03, 6.26694752e-01,
        -1.75389217e+02, 1.80282590e+02, 6.68985691e+00, 7.25841970e+01,
        -1.92181654e+02, 2.04998831e+02, 5.31337709e+00, 9.49673800e+01,
        -2.26249423e+02, 2.03678949e+02, 2.12766425e+00, 9.29826509e+01])

        training_stds = np.array([0.14516509, 0.8142005, 0.48051255, 0.18567251, 0.40096911, 0.65165174,
        0.28202316, 0.13935595, 0.55168162, 0.71887009, 0.38452418, 0.26946467,
        81.17522337, 64.95949447, 25.66205127, 33.23843898, 77.26214907, 74.40827269,
        40.37295338, 40.3033543, 33.32367913, 69.51074244, 25.20399847, 19.48149716])
        # Comment this out to get the working version
        #with open('/home/xilinx/BITSTREAM/scaler.pkl', 'rb') as file:
        #    scaler = joblib.load(file)
        #bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
        #overlay = Overlay(bitstream_path)
        #predictor = predict_model(overlay)
        print("Allocating buffers")
        self.N_FEATURES = 24
        self.N_ACTIONS = 7
        self.input_buffer = allocate(shape=(self.N_FEATURES,), dtype=np.float32)
        self.output_buffer = allocate(shape=(self.N_ACTIONS,), dtype=np.float32)
        data = pd.DataFrame(data)
        data.to_csv('df_pre_aggregate.csv', mode='a', index=False, header=False)
        data = self.dataAggregator(data)
        data.to_csv('df_post_aggregate.csv', mode='a', index=False, header=False)
        data = data.values #this would already have flattened it out
        data = (data - training_means) / training_stds
        #data.to_csv('df_post_scaling.csv', mode='a', index=False, header=False)
        # Comment this out to get working mode
        #data = scaler.transform(data) #apply standard scaler
        #data = torch.tensor(data, dtype=torch.float32) #turn it into torch tensor
        

        print("AI is predicting now")
        predict_results = self.predict(data)
        print("AI finished predicting")
        prediction = np.argmax(predict_results) 
        print("AI is freeing buffer")
        return prediction

#def main():
#    bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
#    overlay = Overlay(bitstream_path)
#    predictor = predict_model(overlay)
#    df = pd.DataFrame(np.random.uniform(low=-1, high=1, size=(20, 6)))
#    print(df)
#    action = predictor.get_action(df)
#    print(f"Action is: {action}")

#if __name__ == "__main__":
#    main()
