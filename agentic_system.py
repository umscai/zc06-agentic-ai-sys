""" Main function for the project"""
#------------------------------------------------------------------------------
import logging
from config import settings, CustomLogger, get_args
from print_color import print
#import pprint
import utils as ut
from orchestration.assistant import PumpAnomalyAssistant
from db_model.ltm_model import init_ltm_db
from db_model.telemetry_model import init_telemetry_db
from orchestration.graph import init_checkpoint_db

import time
#------------------------------------------------------------------------------
def main():
    args=get_args()
    print('Telemetry', tag='Check-dB', tag_color='cyan', color='yellow')
    init_telemetry_db()
    print('LTM', tag='Check-dB', tag_color='cyan', color='yellow')
    init_ltm_db()
    print('Checkpoint', tag='Check-dB', tag_color='cyan', color='yellow')
    init_checkpoint_db()
    print(f'{settings.USE_CONTEXT}', tag='Use LTM as Context', tag_color='cyan', color='red')
    print('+'*100)
    asset_id = args.asset
    test_case_id = args.test
    num_samples = args.samples
    _ = CustomLogger(log_dir=settings.LOG_DIR, save_format=args.format,verbose=args.verbose)
    logger = logging.getLogger(__name__)

    df_cfg = ut.get_asset_test_case(asset_index=asset_id, test_case_index=test_case_id)
    df = ut.generate_test_case_data(df_cfg, num_samples=num_samples)
    logger.info(f"Running test case-{test_case_id} for asset-id:{asset_id} with {num_samples} samples.")

    #print(f"Running test-case-{test_case_id} for asset-id:{asset_id} with {num_samples} samples.")
    print(f"Test-case-{test_case_id} for asset-id:{asset_id} with {num_samples} samples.", tag='Running', tag_color='cyan', color='green')
    logger.debug({"msg": "init","status":"success"})
    try:
        assistant = PumpAnomalyAssistant()
        for telemetry in df.to_dict(orient='records'):
            #time.sleep(.5) # make sure not faster than 1 sample per seconds!
            print('+'*100)
            print(f"{telemetry}", tag='TELEMETRY', tag_color='blue', color='yellow')
            result=assistant.run(asset_id, telemetry)
            if result.get('success',False):
                state=result.get('state',{})
                #msg = state.get('messages',[])
                #print(f'{len(msg)}', tag='MSG-LEN', tag_color='yellow', color='white')
                #tokens=assistant.llm.get_num_tokens_from_messages(msg)
                #print(f'{tokens}', tag='TOKENS', tag_color='yellow', color='white')

                is_anomaly = state.get('is_anomaly', False)
                if is_anomaly:
                    anomaly_class= state.get('classification_class', '')
                    # severity_bands= state.get('severity_bands',{})
                    # output={
                    #     'failure': state.get('primary_failure_mode', ''),
                    #     'root_cause':state.get('root_cause_analysis', ''),
                    #     'action': state.get('action', ''),
                    #     'confidence': state.get('confidence', ''),
                    #     'VFD': state.get('VFD', 0),
                    # }
                    print(f"Anomaly: {anomaly_class}", tag='RESULT', tag_color='red', color='white')
                    #print(f"{severity_bands}", tag='SEVERITY BANDS', tag_color='purple', color='yellow')
                    #print(output)
                    #print('-'*100)
                    #print(state.get('context',''))
                    print(f"{state.get('response')}")
                else:
                    print(f"Not Anomaly", tag='RESULT', tag_color='green', color='white')

    except Exception as e:
        logger.error(f"Error in assistant or main-telemetry loop: {e}")
        print(f"\nUnexpected error: {str(e)}", color='red')

#------------------------------------------------------------------------------
if __name__ == "__main__":

    main()
