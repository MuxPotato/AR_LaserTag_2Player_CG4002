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
            -1.90962226e+00,  1.39242506e+00, -5.90442218e-01,  8.89530801e-01,
            -1.67562779e+00,  1.39851727e+00, -2.60805762e-01,  5.81069672e-01,
            -1.50310697e+00,  1.60335835e+00,  2.77196810e-03,  6.84981199e-01,
            -1.96103782e+02,  2.10622170e+02,  4.51274501e+00,  8.80286848e+01,
            -2.14883103e+02,  2.16385655e+02, -7.00096104e+00,  1.09626191e+02,
            -2.25973069e+02,  2.39611278e+02,  1.38321456e+01,  1.14691192e+02])
        training_stds = np.array([ 0.13731101,  0.81923698,  0.36464978,  0.25399503,  0.36299928,
            0.61870706,  0.21290258,  0.13678906,  0.48915355,  0.56911221,
            0.21004303,  0.26973834, 58.75444345, 48.88679363, 24.78906981,
            27.97908655, 58.97611186, 49.17956258, 48.96525136, 41.34978185,
            33.91183683, 21.14788486, 35.14959351, 18.08821808])
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
