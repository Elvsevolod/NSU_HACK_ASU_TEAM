"""Explicit source corrections; preserve the older oracle files byte for byte."""
import hashlib,json
from copy import deepcopy
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    output=V/'development/oracles/legacy-v2';assert not output.exists();output.mkdir(parents=True)
    for name in ('petclinic-customers','piggymetrics-account'):
        path=V/'validation_inputs/legacy-real'/name/'oracle.json';old=json.loads(path.read_text());new=deepcopy(old)
        new.update(version=2,previous_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   fixed_before_prediction=False,review_basis='Source review after legacy failure; no analyzer behavior is changed to match the oracle',
                   scope='legacy HTTP regression; aggregate graph plus explicit wire/actual args/scalar table fields, not a new holdout')
        if name=='petclinic-customers':
            sid='scenario:clinic-journey';base='method:customers:Owner#';tos=base+'toString()'
            for method in ('toString()','getId()','getFirstName()','getLastName()'):
                new['edges'].append({'source':sid,'relation':'executes','target':base+method})
            new['edges'].append({'source':'method:customers:OwnerResource#updateOwner(int,OwnerRequest)','relation':'calls','target':tos})
            for method in ('getId()','getFirstName()','getLastName()'):
                new['edges'].append({'source':tos,'relation':'calls','target':base+method})
            new['source_evidence']=[
                {'file':'spring-petclinic-customers-service/src/main/java/org/springframework/samples/petclinic/customers/web/OwnerResource.java','line':98,'fact':'update logs ownerModel before save'},
                {'file':'spring-petclinic-customers-service/src/main/java/org/springframework/samples/petclinic/customers/model/Owner.java','line':88,'fact':'source toString calls getId/getLastName/getFirstName and native ToStringCreator'}]
            new['state_probe']={'updated_id':1,'updated_fields':{'firstName':'Joe','lastName':'Smith','address':'Oak','city':'Leeds','telephone':'11223'},
                'generated_identity':'same non-null Integer symbol, distinct from 1, from create response through later lists',
                'row_counts_after_update':{'customers.owners':2,'customers.pets':0,'customers.types':0}}
        else:
            new['steps'][1]['status']=400
            new['edges'].append({'source':'scenario:finance-refusal','relation':'executes',
                                 'target':'method:account:ErrorHandler#processValidationError(IllegalArgumentException)'})
            new['source_evidence']=[{'file':'account-service/src/main/java/com/piggymetrics/account/service/AccountServiceImpl.java','line':46,'fact':'Assert rejects duplicate before remote auth and save'},
                {'file':'account-service/src/main/java/com/piggymetrics/account/controller/ErrorHandler.java','line':17,'fact':'IllegalArgumentException maps to HTTP BAD_REQUEST 400'}]
        (output/(name+'.oracle-v2.json')).write_text(json.dumps(new,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':main()
