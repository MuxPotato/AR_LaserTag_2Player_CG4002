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
        [-1.89645599e+00, 1.39557918e+00, -5.22633517e-01, 8.83336058e-01,
        -1.63571215e+00, 1.35435115e+00, -2.26673508e-01, 5.69341037e-01,
        -1.51253187e+00, 1.63839757e+00, 1.50254386e-02, 6.98686880e-01,
        -1.87847028e+02, 2.10250960e+02, 6.51092312e+00, 8.29576700e+01,
        -2.12354182e+02, 2.19080752e+02, 2.44238631e+00, 1.11272113e+02,
        -2.20761200e+02, 2.37293103e+02, 1.90115133e+01, 1.09655993e+02])

        training_stds = np.array([0.17803033, 0.79733118, 0.43612855, 0.24743565, 0.40751768, 0.60914707,
        0.22944952, 0.14366339, 0.50806402, 0.51698128, 0.22761618, 0.26022468,
        56.96920723, 50.24727656, 25.09333277, 25.85263091, 57.03471338, 50.5334602,
        41.83609903, 42.10649188, 36.86668485, 29.95317528, 30.79357277, 20.06822626])
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
