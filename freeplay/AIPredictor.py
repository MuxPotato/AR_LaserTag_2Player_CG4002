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
        training_means = np.array([
        [-1.90106411e+00,  1.42223929e+00, -5.21434189e-01,  8.84185166e-01,
        -1.60254667e+00,  1.35064750e+00, -2.14327775e-01,  5.64514346e-01,
        -1.49587213e+00,  1.64991546e+00,  4.30985801e-02,  6.93150586e-01,
        -1.84978313e+02,  2.09799990e+02,  5.63194441e+00,  8.10480760e+01,
        -2.09948544e+02,  2.18552303e+02,  4.69849789e+00,  1.10015537e+02,
        -2.20787255e+02,  2.31430751e+02,  1.61396936e+01,  1.08225404e+02]])

        training_stds = np.array([0.15596728, 0.80108595, 0.40933605, 0.2376632,  0.42493601, 0.60134487,
        0.23424368, 0.15549933, 0.52428828, 0.51300686, 0.19228889, 0.26355529,
        56.95933789, 50.33420059, 23.79799618, 25.2051356,  59.09344824, 49.73347988,
        42.11901124, 41.49199453, 37.83285518, 37.72460961, 32.35132605, 20.65105318])
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
