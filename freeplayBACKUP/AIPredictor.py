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
        training_means = np.array([-1.90133850e+00, 1.39720304e+00, -6.10352909e-01, 8.79665225e-01,
        -1.63582021e+00, 1.40125682e+00, -2.43365175e-01, 5.72979956e-01,
        -1.49996782e+00, 1.66264083e+00, 1.94456647e-02, 6.99365942e-01,
        -1.89175431e+02, 2.10820321e+02, 5.54273526e+00, 8.47832722e+01,
        -2.11187061e+02, 2.19060992e+02, -6.64791032e-01, 1.11251283e+02,
        -2.21130606e+02, 2.37185718e+02, 1.68432704e+01, 1.10903345e+02])
        training_stds = np.array([
            0.16455244, 0.80233053, 0.34850048, 0.24333963, 0.41612518, 0.60755705,
            0.21175238, 0.14314562, 0.50619868, 0.52362814, 0.21811505, 0.25914689,
            57.39660831, 48.6776659, 25.31180755, 26.86858041, 58.03887113, 48.89653878,
            43.28553021, 42.59837441, 37.56639716, 28.22495288, 32.66675253, 19.03416885
        ])
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
