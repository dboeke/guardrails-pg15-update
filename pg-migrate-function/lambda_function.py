from __future__ import print_function
import json
import boto3
import psycopg2
import uuid
import os
import time
import logging
import cfnresponse

# initialise logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
print('Logging configured')

def reset_master_user(client, host, password):
    response = client.modify_db_instance(
        DBInstanceIdentifier=host,
        ApplyImmediately=True,
        MasterUserPassword=password
    )
    print('Got Response')
    print(response)
    result = None
    if 'DBInstance' in response:
        result = {
            'MasterUserName': response['DBInstance']['MasterUsername'],
            'Endpoint': response['DBInstance']['Endpoint']['Address'],
            'Port': response['DBInstance']['Endpoint']['Port'],
            'Version': response['DBInstance']['EngineVersion'],
            'Password': password,
            'DBName': response['DBInstance']['DBName']
        }
    print(f'Got Result: {result}')
    return result

def run_query(dbInfo, action, workspace):
    conn = psycopg2.connect(
        user=dbInfo['MasterUserName'], 
        password=dbInfo['Password'], 
        host=dbInfo['Endpoint'], 
        port=dbInfo['Port'],
        database=dbInfo['DBName'],
        sslmode='require'
    )

    cur = conn.cursor()

    if action == 'getVersion':
        print('Getting DB Version')
        query = "SELECT version() AS version"
        cur.execute(query)
        results = cur.fetchone()
        print("Running Query: {}".format(query))

    triggers = {
        "control_category_path_au": "control_categories",
        "control_resource_category_path_au": "resource_categories",
        "control_resource_types_path_au": "resource_types",
        "control_types_path_au": "control_types",
        "policy_category_path_au": "control_categories",
        "policy_resource_category_path_au": "resource_categories",
        "policy_resource_types_path_au": "resource_types",
        "policy_types_path_au": "policy_types",
        "resource_resource_category_path_au": "resource_categories",
        "resource_resource_type_path_au": "resource_types",
        "resource_types_500_rt_path_update_au": "resource_types",
        "resources_update_to_deactivate_grants_au": "resources"
    }

    triggers_path = {
        "control_category_path_au": "types_path_au('controls', 'control_category_id', 'control_category_path')",
        "control_resource_category_path_au": "types_path_au('controls', 'resource_category_id', 'resource_category_path')",
        "control_resource_types_path_au": "types_path_au('controls', 'resource_type_id', 'resource_type_path')",
        "control_types_path_au": "types_path_au('controls', 'control_type_id', 'control_type_path')",
        "policy_category_path_au": "types_path_au('policy_values', 'control_category_id', 'control_category_path')",
        "policy_resource_category_path_au": "types_path_au('policy_values', 'resource_category_id', 'resource_category_path')",
        "policy_resource_types_path_au": "types_path_au('policy_values', 'resource_type_id', 'resource_type_path')",
        "policy_types_path_au": "types_path_au('policy_values', 'policy_type_id', 'policy_type_path')",
        "resource_resource_category_path_au": "types_path_au('resources', 'resource_category_id', 'resource_category_path')",
        "resource_resource_type_path_au": "types_path_au('resources', 'resource_type_id', 'resource_type_path')",
        "resource_types_500_rt_path_update_au": "update_types_path()",
        "resources_update_to_deactivate_grants_au": "resources_hierarchy_deactivate_grants_au()"
    }

    triggers_when = {
        "control_category_path_au": "(old.path is distinct from new.path)",
        "control_resource_category_path_au": "(old.path is distinct from new.path)",
        "control_resource_types_path_au": "(old.path is distinct from new.path)",
        "control_types_path_au": "(old.path is distinct from new.path)",
        "policy_category_path_au": "(old.path is distinct from new.path)",
        "policy_resource_category_path_au": "(old.path is distinct from new.path)",
        "policy_resource_types_path_au": "(old.path is distinct from new.path)",
        "policy_types_path_au": "(old.path is distinct from new.path)",
        "resource_resource_category_path_au": "(old.path is distinct from new.path)",
        "resource_resource_type_path_au": "(old.path is distinct from new.path)",
        "resource_types_500_rt_path_update_au": "(old.path is distinct from new.path)"
    }

    if action == 'disableTriggers':
        results = []
        for trigger in triggers:
            query = "DROP TRIGGER {} on {}.{};".format(trigger, workspace, triggers[trigger])
            print(query)
            try:
              result = cur.execute(query)
            except Exception as e:
                print(e)
                conn.rollback()
                results.append(str(e))
            else:
                conn.commit()
                results.append(result)

    if action == 'enableTriggers':
        results = []
        for trigger in triggers:
            query = "CREATE TRIGGER {} after update on {}.{} for each row when {} execute procedure {}.{};".format(
                trigger, 
                workspace, 
                triggers[trigger],
                triggers_when[trigger],
                workspace,
                triggers_path[trigger]
            )
            print(query)
            try:
              result = cur.execute(query)
            except Exception as e:
                print(e)
                conn.rollback()
                results.append(str(e))
            else:
                conn.commit()
                results.append(result)

    if action == 'updatePgExtensions':

        query  = "select * from pg_extension order by extname;"
        print(query)
        try:
            cur.execute(query)
            result = cur.fetchall()
        except Exception as e:
            print(e)
        else:
            print(result)

        pg15Extentions = {
            "hstore": '1.8',
            "ltree": '1.2',
            "pg_trgm": '1.6',
            "plpgsql": '1.0', 
            "plv8":  '3.1.6'
        }

        pgExtentions = {
            "hstore": '1.7',
            "ltree": '1.2',
            "pg_trgm": '1.5',
            "plpgsql": '1.0', 
            "plv8":  '2.3.15'
        }

        if dbInfo['Version'].startswith('15'):
            pgExtentions = pg15Extentions

        results = []
        for extention in pgExtentions:
            query = "ALTER EXTENSION {} UPDATE TO '{}';".format(extention, pgExtentions[extention])
            print(query)
            try:
              result = cur.execute(query)
            except Exception as e:
                print(e)
                conn.rollback()
                results.append(str(e))
            else:
                conn.commit()
                results.append(result)
    
    cur.close()
    conn.commit()

    return results

def handler(event, context):
    # Initialise
    DB_HOST = os.environ['DB_HOST']
    action = event['ResourceProperties']['Action']
    workspace = event['ResourceProperties']['Workspace']
    print("Host: {}".format(DB_HOST))
    print("Action: {}".format(action))
    print("Workspace: {}".format(workspace))
    print("Init Complete")
    
    # Reset DB Master User'
    print('Getting DB Credentials')
    client = boto3.client('rds')
    print("DB Master User Reset Start")
    dbInfo = reset_master_user(client, DB_HOST, str(uuid.uuid4()))
    if dbInfo is None:
        raise Exception(f'Error Resetting Password on DB: {DB_HOST}') 
    print("Master User DB Reset Requested")
    DbUpdating = True
    while(DbUpdating):
        time.sleep(10)
        response = client.describe_db_instances(
            DBInstanceIdentifier=DB_HOST,
            MaxRecords=20
        )  
        print("Found {} matching DBs".format(len(response['DBInstances'])))
        status = response['DBInstances'][0]['DBInstanceStatus']
        pendingValues = response['DBInstances'][0]['PendingModifiedValues']
        DbUpdating = ((status != 'available') or ('MasterUserPassword' in pendingValues))
        print('DB Status: {}'.format(status))
        print('Pending Values: {}'.format(pendingValues))
        print('DB Updating: {}'.format(DbUpdating))
    print("DB Connect completed")

    # Process Action
    if event['RequestType'] == 'Create':
        LOGGER.info('CREATE!')
        responseValue = {"Message": "Resource creation successful!"}
    elif event['RequestType'] == 'Update':
        LOGGER.info('UPDATE!')
        print(f'Action: {action}')
        responseValue = run_query(dbInfo, action, workspace)
        print(responseValue)
    elif event['RequestType'] == 'Delete':
        LOGGER.info('DELETE!')
        responseValue = {"Message": "Resource deletion successful!"}
    else:
        LOGGER.info('FAILED!')
        responseValue = {"Message": "Unexpected event received from CloudFormation"}

    # Send Response
    responseData = {}
    responseData['Data'] = responseValue
    cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData, "CustomResourcePhysicalID")