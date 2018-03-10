import boto3
import os

ec2_resource = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
elb_client = boto3.client('elb')


def ec2_create_key(keyname):
    my_path = os.path.expanduser("~/" + keyname + "_ssh.pem")

    try:
        if os.path.exists(my_path) and os.path.getsize(my_path) > 0:
            print("Warning!!! Key wasn't created because " + my_path + " already exists")
            return 0
        else:
            keypair = ec2_client.create_key_pair(KeyName=keyname)

            print("Key is being exported to " + my_path)
            with open(my_path, "w+") as line:
                print(keypair['KeyMaterial'], file=line)
                print(keypair['KeyMaterial'])
            line.close()
            return 1
    except:
        return 0


def ec2_create_sg(type, sgname):
    try:
        if type == 'ssh':
            response = ec2_client.create_security_group(GroupName=sgname, Description='SG for ssh')
            ec2_client.authorize_security_group_ingress(
                GroupId=response['GroupId'],
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ]
            )
            print("Security GroupID {} was crated".format(response['GroupdId']))
            return 1
        elif type == 'web':
            response = ec2_client.create_security_group(GroupName=sgname, Description='SG for web')
            ec2_client.authorize_security_group_ingress(
                GroupId=response['GroupId'],
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 443,
                     'ToPort': 443,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp',
                     'FromPort': 80,
                     'ToPort': 80,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ]
            )
            print("Security GroupID {} was crated".format(response['GroupdId']))
            return 1
        else:
            print("Security Group creation process had failed, unknown type!")
            return 0
    except:
        print("Security Group creation process had failed, very likely due to duplicate SG Naming!")
        return 0


def create_ec2_instance(sg, key, user_data):
    instance = ec2_resource.create_instances(ImageId='ami-f2d3638a', MinCount=1, MaxCount=1, SecurityGroups=[sg],
                                             KeyName=key, UserData=user_data, InstanceType='t2.micro')
    return instance


def elb_create_lb(lbname, sg_id, az):
    # try:
    lb = elb_client.create_load_balancer(
        LoadBalancerName=lbname,
        Listeners=[
            {
                'Protocol': 'HTTP',
                'LoadBalancerPort': 80,
                'InstanceProtocol': 'HTTP',
                'InstancePort': 80
            }
        ],
        AvailabilityZones=az,
        SecurityGroups=[
            sg_id
        ],
        Tags=[
            {
                'Key': lbname
            }
        ]
    )

    elb_client.modify_load_balancer_attributes(
        LoadBalancerName=lbname,
        LoadBalancerAttributes={
            'CrossZoneLoadBalancing': {
                'Enabled': True
            },
            'AccessLog': {
                'Enabled': False
            },
            'ConnectionDraining': {
                'Enabled': True,
                'Timeout': 60
            },
            'ConnectionSettings': {
                'IdleTimeout': 60
            }
        }
    )

    elb_client.configure_health_check(
        LoadBalancerName=lbname,
        HealthCheck={
            'Target': 'TCP:80',
            'Interval': 10,
            'Timeout': 5,
            'UnhealthyThreshold': 5,
            'HealthyThreshold': 5
        }
    )

    print("LB is created, DNS: {}".format(lb['DNSName']))
    return 1
    # except:
    #     print("Something went wrong!!!!!")
    #     return 0


sg_name = "web_sg5"
key_name = "web_key5"
user_data = "#!/bin/bash\nsudo yum install httpd -y\nsudo service httpd start\nsudo chkconfig httpd on"
user_data = user_data + "\nhostname > /var/www/html/index.html"

# Create EC2 SG
ec2_create_sg("web", sg_name)

# Create EC2 Key
ec2_create_key(key_name)

# Create EC2 instance
instanceid1 = create_ec2_instance(sg_name, key_name, user_data)
instanceid2 = create_ec2_instance(sg_name, key_name, user_data)

print(instanceid1[0].id)
print(instanceid2[0].id)

# Create ELB
az = ["us-west-2a", "us-west-2b", "us-west-2c"]
elb_create_lb("lb3", "sg-4881b037", az)
#
# #Attach EC2 instances
elb_client.register_instances_with_load_balancer(LoadBalancerName='lb3', Instances=[{'InstanceId': instanceid1[0].id},
                                                                                    {'InstanceId': instanceid2[0].id}])

# Use the filter() method of the instances collection to retrieve
# all running EC2 instances.
instances = ec2_resource.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    print(instance.id, instance.instance_type)
