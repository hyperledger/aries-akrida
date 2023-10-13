# Load Agent using Locust

Locust is an open source load testing tool. Locust allows defining user behaviour with Python code, and swarming your system with millions of simultaneous users.

For more information about why locust was chosen, or the design document, please see here.

Before proceeding, please make sure you have a billing account set up on your cloud provider and that you will have enough permissions to create and deploy VM instances and other architectures.

## Non-Clustered Environment

It is recommended to complete this section before attempting to proceed with the instructions for spinning the load testing framework in a clustered environment.

To set up our load testing framework, we will begin by creating a non-clustered environment. This will help in ( a ) building out each of the components and ensuring that they work, ( b ) making sure a simpler version of our desired environment works in the first place, and ( c ) allowing us to make instance templates of these VMs to later scale.

We will break this part up into the following sections:

- How to SSH into VMs on the Cloud,
- Adding SSH Keys to Individual VMs, and
- Instantiating VMs on the Cloud. This latter part will include setting up:
  - a Postgres Database (for agent configuration),
  - an ACA-Py Agent,
  - locust, and
  - a Mediator,

as well as setting up firewall rules and more.

_(Not all of these components may be necessary, if you already have these components built out (e.g. like a ACA-Py agent or your own mediator)): Regardless, we will still walk through each of these sections: upping a mediator on the cloud, an ACA-Py agent, a Postgres database (for the ACA-Py agent configuration to be saved), and the load testing framework. _

However, before we can do that, we need to have SSH keys on our computer, so that we can SSH into those machines.

### Intiantiating Necessary VMs on the Cloud

In order to be able to set up our environment, we will need to instantiate 3-4 VMs initially for a non-clusterered environment:
(1) A Postgres Database (for the ACA-Py agent configuration),
(2) An ACA-Py agent,
(3) A VM for locust, and
(4) (Optional) a mediator.

This section will constitute the initial, same set-up for each of these VMs that will need to be followed. From there, we can head into the individual sections.

First of all, head into your designated cloud provider. For the sake of these instructions, we will make the assumption that you are working with AWS.

In order to log in, you will need to follow the instructions given to you by your organization. Ensure, before proceeding, that you have sufficient permissions to be able to at least spin up and down EC2 instances and modify rules for security groups.

After logging in, press the menu bar dropdown on the left-hand side. Head to `Instances > Instances`. From there, on the top right side (next to your email or username), choose the region you want to work from and spin your environment up in.

_Pro Tip: If you're not taken to a page with a drop-down menu on the left-hand side, search for "Instances" in the search bar at the top of the page._

For the sake of these instructions, we will spin our environment up in `us-east-1` (which will be reflected in the tutorial videos). Choose whatever suits your needs best. (However, for whichever choice you make, make sure ALL of your VMs are spun up in the same zone. Putting VMs in different zones WILL have an adverse effect on latency when running the performance tests.)

### Instantiating First Instance

Now it is time to spin up one of these VMs. After heading into the `Instances > Instances` menu and deciding the zone you want to work in, go ahead and click on the orange `Launch Instances > Launch Instances`. This will send you the page in order to be able to create a VM.

##### Names and tags

Go ahead and give this first VM an appropriate name. We will go in order as above and, thus, give this first VM the very creative name of `database`.

##### Application and OS Images (Amazon Machine Image)

Under `Application and OS Images (Amazon Machine Image)`, navigate to the `Quick Start` section and press `Ubuntu`.

##### Instance type

Under `Instance Type`, click on the box below `Instance Type` (it should be set to `t2.micro` by default). For now, type in and set this to `t3a.small`.

**Important note: for the `locust` VM, you will need to give it plenty of disk size!** Further, if you want to spin up more users, it's recommended to user a bigger VM. To begin with, maybe choose a `t3.large` or `t3.xlarge`. However, definitely, head under the `Configure storage` section and change the `8 GiB` to `32 GiB` or `64 GiB`.

##### Key pair (login)

If this is the first VM you are creating for this work,

- under `Key pair (login)` click on `Create new key pair`. A new subwindow should pop up, titled `Create key pair`. Create a name for this key pair, in the box with the text "Enter key pair name". We will give it the very creative name `performance`. Choose a key pair type. We went with RSA. Finally, choose `.pem` as your private key pair type. Press `Create key pair`. From here, you will want to save the key pair in a nice, comfortable location, perferably in a folder you will be able to recognize as having SSH key pairs. For example, in these instructions, we will be saving it under the folder `Indicio/perf/services/aws`. Press save.

If this is NOT the first VM you are creating for this work,

- click on the box under `Key pair name` navigate to the key pair you have previously created for this project. For us, since our previously extremly creative name of our key pair was `performance`, we'll click on this.

##### Network Settings

If this is the first VM you are creating for this work,

- under `Network settings`, click the `Edit` box.
- Under `Firewall (security groups)`, click on the `Create security group` box.
- Under `Security group name`, give this securite group a name. Consider, for example, `performance security group` or `performance-testing`.

This is sufficient to create the security group.

_If you are precautious about the first security rule down below, allowing SSH from anywhere, the key pair must be attached to the instance (so it's less dangerous). This is what you are doing in the key pair step. If you are wary about this though, you can go ahead and change the `Source type` to `My IP`. Please note: by doing this, if you move locations/your IP changes, you'll have to update this in this respective security group's rules in order to be able to SSH back into the instance._

If this is NOT the first VM you are creating for this work,

- under `Firewall (security groups)`, click the `Select existing security group` box.
- Click on the box under `Common security groups`. Select the previous security group you created for this project (in our case, `performance-testing`).

##### Launch instance

Finally, scroll to the bottom of the page and press the orange `Launch instance button`.

Go ahead and repeat the above process, while you are here for all of the respective instances you will need for the non-clustered environment.

### SSHing Into New Instances

#### Giving Read Permissions

Now, we will proceed to navigate our way into these new instances we created. First of all, recall the directory in which you saved your key pair for each of these VMs. From our instructions, we saved this under `Indicio/perf/services/aws`, so this will be the directory we will be using. Open up a terminal and navigate there, AKA

```
cd Indicio/perf/services/aws
```

or where-ever you saved your key pair. You can double-check your key pair is in the respective folder by doing `ls | grep ".pem"`.

We will need to allow read permission to this key file (otherwise, SSHing will fail). We can do this by doing, for example,

```
chmod 0400 performance.pem
```

if your `.pem` file is named `performance.pem`. Just change the name of your file respectively. Now you're ready to SSH into the instances you just created!

Stay here [terminal-wise]. In your browser, navigate back to that `Instances > Instances` page. There should now be four VMs that you created. Each of these VMs should have a name, so you can differentiate between each one. Let's SSH into the VMs in the same order that we created them.

Click on the database instance by clicking on the instance ID to the right of it (within the same row). Copy the IP under `Pubic IPv4 address`. Now head back to your terminal.

In your terminal (please be in the same directory as that `.pem` key pair), execute

```
ssh -i performance.pem ubuntu@publicIP
```

Replace `performance.pem` with the name of YOUR `.pem` key pair and replace `publicIP` with the IP you just copied above.

In this case, the `ubuntu` is representative of the default account name on any ubuntu instance.

If the terminal prompts you with `Are you sure you want to continue connecting?`, go ahead and type `yes`.

Congrats, spy! You're in!

Let's go ahead and do this to the other 2-3 instances, so we can do all of the installations at once. If it's easier, you can also type, for example, `echo "database"` (or `echo "whichever VM you're using"`) so you can tell which VM is which. :)

_Clarification: This is all in separate terminal windows or tabs, so you're never officially closing one (yet)!_

For SSHing into the remaining VMs, you will also need to be in the same location with that `.pem` key each time you SSH into the respective VM. (Additionally, follow the attached video if you have any difficulties! Just remember to replace the directory and `.pem` key pair names!)

### Installation Instructions

Finally! We're in!

Now, probably the easiest bit, copy and paste the following installation instructions into each of those SSH sessions:

```
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y docker.io git tmux htop sysstat iftop tcpdump
sudo curl -SL https://github.com/docker/compose/releases/download/v2.7.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
sudo chmod a+x /usr/local/bin/docker-compose
```

If any of the VMs ask to restart any of the services, just press the return or enter key on your keyboard (while that terminal is selected). This may take a few moments, so feel free to snack on your favorite snack. :)

##### SSH Keys

Awesome! Now that each of those are done, let's add SSH keys to each of these VMs, so we can go ahead and clone down the necessary resources.

Once again, we will need to do this step for each of our VMs. We will start with the first one [the database] in the list and then rinse and repeat for the remaining VMs.

To generate an SSH key, execute

```
ssh-keygen -t ed25519 -C example@example.com
```

where `example@example.com` is the email associated with your GitHub account, or whichever email has access to these repos.

- Under the `Enter file in which to save the key`, just press `Return` or `Enter` on your keyboard.
- Under `Enter passphrase (empty for no passphrase)`, we would recommend using a passphrase! Go ahead and put something in! (This will be analogous to a password (literally, called a keychain) in this instance).
- ^You will be asked to enter this passphrase in again.

Then, to start up an SSH agent, execute

```
eval "$(ssh-agent -s)"
```

To edit `~/.ssh/config`, without necessarily entering a text editor, execute:

```
echo "Host *" > ~/.ssh/config
echo "    AddKeysToAgent yes" >> ~/.ssh/config
echo "    IdentityFile ~/.ssh/id_ed25519" >> ~/.ssh/config
```

To confirm that this has been edited properly, go ahead and execute `cat ~/.ssh/config`.

To add a ssh key:

```
ssh-add ~/.ssh/id_ed25519
```

Great! Now we need to communicate to GitHub the public part of our key. You can go ahead and read out the public part of the key by doing

```
cat ~/.ssh/id_ed25519.pub
```

(or whatever you called it from earlier).

This would be a good point in the process to go ahead and repeat this whole SSH key section, for each of the remaining SSH sessions, before proceeding with the following steps.

After catting / printing out the public part of the key from the first VM, go ahead and open up GitHub in your browser. Head to Settings. Then, on the left-hand side, head to `Access > SSH and GPG Keys`. Click on the green `New SSH Key`.

Under title, give this SSH key a respective title to the VM. If we "stick with" that first VM, let's call this something like `aws-database`. In the `Key` box, go ahead and paste the output from the cat command from the first SSH session from earlier (end of your email included!). Then click the green `Add SSH Key` button.

At this point, you may be prompted for your GitHub password. Go ahead and enter it.

Boom! You've added an SSH Key for that first VM! :) Please go ahead and repeat this process (communicating the SSH keys to GitHub) for the remaining SSH sessions.

After adding all of the SSH keys to GitHub, we now need to verify our key is added. In each of those VMs, execute

```
ssh -T git@github.com
```

If any prompts prompt you with `Are you sure you want to continue connecting?`, go ahead and type `yes`.

Bam! You should be good to clone down all of the content we will need now! Let's save this portion though for each of the individual sections :) We'll see you there!

# Instantiating VMs on the Cloud

## Postgres DB (ACA-Py Agent Configuration)

First, before any worthwhile adventure, we must grab some resources. We can do this by cloning down the [aries-akrida](https://github.com/Indicio-tech/aries-akrida) repository. Do so, by doing

```
git clone git@github.com:Indicio-tech/aries-akrida.git
```

Go ahead and navigate into this repo by doing `cd aries-akrida`. From there, we will want to take all of the relevant files we will need (without really needing the rest). We can do that by

```
cd instance-configs/database
mv * ../../../
cd ../../../
rm -rf aries-akrida/
```

so that we are only left with the relevant files in the database directory for this VM. From there, we will need to populate the `.env` file. Please make sure you fill out the following below information (i.e. don't blindly copy and paste). However, once the below information is filled out, we can put it into the environment by

```
# Set this to something secure
echo "REDIS_PASSWORD=" > .env

# Set this to your own ledger genesis URL
echo "ACAPY_GENESIS_URL=https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/genesis_files/pool_transactions_testnet_genesis" >> .env
echo "POSTGRES_USER=test" >> .env
echo "POSTGRES_PASSWORD=test" >> .env
```

where `REDIS_PASSWORD` is something secure that you will have access to, `ACAPY_GENESIS_URL` is the genesis url of the ledger you will be using (we provided Indicio's by default), and you've filled out a username and password for `POSTGRES_USER` and `POST_GRES_PASSWORD`, respectively.

From there, we're almost ready to spin everything up; however, before we do so, we need to set some firewall rules.

### Firewall rules (Postgres DB)

We have decided to put these firewall rules, instead of doing them all at once, do them under their respective section. For each of these firewall rules, you're more than welcome to inspect each of the docker-compose files, which is what is motivating each of the firewall rules.

For the postgres DB, [if you investigate the `docker-compose.yml`] we will need to allow traffic in on ports `5432` and `6379` for the `holder-db` and `redis-host`, respectively.

In order to do this, please make sure that you have sufficient permissions within AWS to be able to edit, add, and remove rules within security groups.

Let's go ahead and head to the browser. Log into AWS. From earlier, if you aren't there already, navigate back to the zone you were previously working in (recall, we chose to work in the `us-east-1` zone). Click on the menu icon on the left side of your screen. Click on `Instances > Instances`. From here, you should see all of the VMs you have created previously. Additionally, there should be a column will all of the security group names. Give this a quick glance over and make sure all of the VMs that you created belong to the same security group. Click on the `Instance ID` of one of these VMs and copy its IP under its `Private IPv4 Address`. This is the IP address the VM uses to communicate internally within its network or VPC. We care about the first two portions. So, for example, if this IP was `123.45.67.89`, we care about the `123.45` portion. We will use this later. However, we will need the full private IP address for later, **_so it's recommended at this step to record this internal IP address down somewhere to save for later._** (label it database)

Now, go back to the menu icon on the left side of your screen. Click on `Network & Security > Security Groups`.

From here, you should see the name of the security group that you created for all of the aforementioned VMs under the `Security group name` column. Click on the ID under `Security group ID` corresponding to the name of the security group you created for your VMs.

Under `Inbound Rules`, click on the box `Edit Inbound Rules`.

Next, click on `Add rule`. Add the following two rules:

1. Allow in interal TCP traffic on port `5432`
   - Type: `Custom TCP`
   - Port Range: `5432`
   - Source: `Custom`
     - `172.31.0.0/16`, where `172.31` is that private bit of the private IP portion from earlier.
2. Allow in internal TCP traffic on port `6379`
   - Type: `Custom TCP`
   - Port Range: `6379`
   - Source: `Custom`
     - `172.31.0.0/16`, where `172.31` is that private bit of the private IP portion from earlier.

Then click the orange `Save rules` button.

Awesome! From there, we should be good to spin everything up. Thus, if you go back to the SSH session with your database VM, we can go ahead and do

```
sudo docker-compose build
sudo docker-compose up
```

_Other than that, just note that if you spin down this VM/environment and want to bring it back up again, you will need to clear out the database. To do this, just do_

```
sudo rm -rf holder-db/ redis*
sudo docker-compose down -v && sudo docker-compose build && sudo docker-compose up
```

Otherwise, we're ready to get up our ACA-Py agent to communicate with this database!

## ACA-Py Agent

If in the last section we packed our toiletries for this adventure, then in this part we're packing our suitcases! (The analogy being that the database portion and ACA-Py agent portion should be working together and communicating.) For this prepatory portion of the adventure, we will once again need that same repo from earlier.

We can do this by cloning down the [aries-akrida](https://github.com/Indicio-tech/aries-akrida) repository. Do so, by doing

```
git clone git@github.com:Indicio-tech/aries-akrida.git
```

Go ahead and navigate into this repo by doing `cd aries-akrida`. From there, we will want to take all of the relevant files we will need (without really needing the rest). We can do that by

```
cd instance-configs/acapy-agent
mv * ../../../
cd ../../../
rm -rf aries-akrida/
```

so that we are only left with the relevant files in the acapy-agent directory for this VM. From there, we will need to populate the `.env` file. However, we will need some information from AWS in order to fill it out.

### Populating .env (ACA-Py Agent)

In your browser, open a tab up with AWS. Click on the menu icon on the left side of your screen. Click on `Instances > Instances`. From here, you should see all of the VMs you have created previously. Click on the `Instance ID` of the `acapy-agent` VM. Copy both its external (`Public IPv4 Address`) IP and internal (`Private IPv4 Address`) IP. **_Record these down somewhere._** (label them ACA-Py, external and ACA-Py, internal, respectively.)

Once again, we will proceed to now fill out the `.env` file. Please make sure to fill out the information in advance (i.e. don't blindly copy and paste). Once the below information is filled out, we can put it into the environment by

```
# External/Public IP of ACA-Py Agent VM
echo "ISSUER= " > .env
# (For way later) This will be our transport load balancer

# Internal/Private IP of Database
echo "DATABASE= " >> .env

# Set this to your own ledger genesis URL
echo "ACAPY_GENESIS_URL=https://raw.githubusercontent.com/Indicio-tech/indicio-network/main/genesis_files/pool_transactions_testnet_genesis" >> .env
# Doesn't need to be test
echo 'ACCOUNT="test"' >> .env
echo 'PASSWORD="test"' >> .env
echo 'ADMIN_ACCOUNT="test"' >> .env
echo 'ADMIN_PASSWORD="test"' >> .env
```

where `ISSUER` is the external or Public IP of the ACA-Py agent VM from earlier, `DATABASE` is the internal or Private IP of the Database VM, `ACAPY_GENESIS_URL` is the genesis url of the ledger you will be using (we provided Indicio's by default), and the remaining variables are accounts and passwords that you're welcome to change (but you might need to remember them).

Before we move onto firewall rules, we need to change one last IP in one of our config files. We will do this by opening an in-line text editor. For this section, go ahead and grab the internal/private IP of the ACA-Py agent VM. Go ahead and do

```
vim configs/issuer.yml
:%s/{INTERNAL_IP}/111.11.11.11
```

and hit enter, where you are replacing the `111.11.11.11` with the internal/private IP of the database VM. To exit the in-line text editor and save your changes, go ahead and type in `:wq` and press enter.

Awesome! This tells our ACA-Py agent to communicate with our database, from the previous step, for information (e.g. anchoring DIDs, schemas, etc.).

However, we'll need to modify our firewall rules again for this communication to actually work.

(Within this `docker-compose.yml`, we also set the `genesis-url`, so it's recommended to go in and change this if you are not using Indicio's genesis url.)

### Firewall rules (ACA-Py Agent)

Once again, we encourage you---the reader---to investigate your `docker-compose.yml` for this section to see the motiviation behind each of the firewall rules.

For the ACA-Py agent VM, [if you investigate the `docker-compose.yml`] we will need to allow traffic in on ports `8150` and `8151` (for the nonclustered portion), for the admin and transport ports for ACA-Py, respectively.

Let's go ahead and head to the browser. Log into AWS. From earlier, if you aren't there already, navigate back to the zone you were previously working in (recall, we chose to work in the `us-east-1` zone). Click on the menu icon on the left side of your screen. Click on `Network & Security > Security Groups`.

From here, you should see the name of the security group that you created for all of the aforementioned VMs under the `Security group name` column. Click on the ID under `Security group ID` corresponding to the name of the security group you created for your VMs.

Under `Inbound Rules`, click on the box `Edit Inbound Rules`.

Next, click on `Add rule`. Add the following rule:

1. Allow yourself access to ports `8150-8151`
   - Type: `Custom TCP`
   - Port Range: `8150-8151`
   - Source: `My IP`

Then click the orange `Save rules` button.

Awesome! From there, we should be good to spin everything up. Thus, if you go back to the SSH session with your database VM, we can go ahead and build our issuer image. This relies on the `acapy-cache-redis` plugin, so we're going to go ahead and build this image locally by doing

```
sudo docker build -f docker/Dockerfile --no-cache -t indicio-tech/aries-mediator .
```

After this is done building, we can do

```
sudo docker-compose up
```

Awesome! Now let's set this ACA-Py agent up to be able to do issuances.

### ACA-Py Agent Configuration

#### Anchoring and Setting DID

In order to be able to have this ACA-Py agent be able to issue credentials to our simulated clients, we need to set it up for success. To do this, we will have to navigate to the ACA-Py Admin UI.

We can do this by going to our browser and using the external/public IP of our ACA-Py agent VM. Suppose, for example, the external IP of our ACA-Py agent VM is `external.ip.of.acapy.agent`. Then, in our browser, we will want to navigate to `http://external.ip.of.acapy.agent:8150`, where `external.ip.of.acapy.agent` is the external/public IP of the ACA-Py Agent VM.

Welcome to the ACA-Py Admin UI! There's a whole lot of API calls here, but we're only interested in a select few. Let's scroll down all the way to the section titled `wallet`.

Within the `wallet` section, click on the $\color{green}{post}$ method $\color{green}{/wallet/did/create}$. This should have the dropdown section extend downwards. Go ahead and click on the box titled `Try it out`. Click on the blue $\color{blue}{Execute}$ button. This will generate you a DID and a verkey.

In a separate tab in your browser, navigate to where you can anchor DIDs to the ledger you chose. For Indicio, this is our [self serve site](https://selfserve.indiciotech.io/). For Indicio, make sure you have selected Indicio TestNet. Then, go ahead and paste the DID and Verkey. (Notice, in the responses, there are two DIDs and Verkey pairs. There's the top (real) one and the bottom (example) one. We want the top pair.) After pasting, go ahead and click the orange `Submit` button. (It's recommended not to close this tab yet or, if you do close this tab, save the DID.)

After submitting, return back to the ACA-Py admin UI. Scroll up to the section titled `ledger`. Under the $\color{blue}{get}$ request, click on the $\color{blue}{/ledger/taa}$ dropdown. We will need to accept the transaction author agreement, for the Indicio ledger (or whatever ledger you are using), in order to be able to successfully associates our DID with this issuer. Under this dropdown, go ahead and click the `Try it out` box. Click the blue $\color{blue}{Execute}$ button.

This will return a rather large response. Copy everything in the `"text"` value; that is, for example... `"Indicio Transaction Author Agreement \n\nVersion... \n\n""`. Make sure to include the beginning `"` and ending `"`.

Then, right below this dropdown menu, click the following $\color{green}{post}$ method with $\color{green}{ledger/taa/accept}$. Click on the `Try it out` button.

Within the `body` section, replace the `"string"` bit corresponding to `"text"` with the bit you copied just before. Under `"mechanism"`, replace that corresponding `"string"` with `"on_file"` (unless told otherwise). Under `"version"`, replace that corresponding `"string"` with `"1.0"`. Thus, if you've done everything right, the JSON body box should look something like:

```
{
  "mechanism": "on_file",
  "text": "Indicio Transaction Author Agreement \n\n...under its own legislation.  \n\n",
  "version": "1.0"
}
```

where, of course, the text string above is much much longer. If everything looks right, go ahead and click the blue $\color{blue}{Execute}$ button.

Awesome! Now we should be able to assign our current public DID. We can do that by returning back to the `wallet` section, going under the $\color{green}{post}$ method titled $\color{green}{/wallet/did/public}$ and clicking it. Click on the `Try it out` button. After clicking on `Try it out`, go ahead and paste the DID you anchored earlier into the `DID of interest` box. Then click the blue $\color{blue}{Execute}$ button.

Amazing! You've now successfully anchored that DID to the ledger and successfully associated that DID with this ACA-Py agent!

#### Creating a Schema

Now let's create a schema, so we can issue some credentials. For this bit, we're going to stick with a super simple credential. However, after going through this process, you're more than welcome to modify the bits to whatever type of credential you're looking for!

Under the same ACA-Py Admin UI, let's head to the section titled `schema`. Click on the $\color{green}{post}$ method titled $\color{green}{/schemas}$ and, again, click on the `Try it out` box. We're just going to use the default schema, as we're just interested in a small, simple credential, but you're welcome to change this (just note you'll need to propagate these changes elsewhere in the `.envs` and code, accordingly). Go ahead and click the blue $\color{blue}{Execute}$ button. Like before when we copied the DID, copy the `schema_id` from the response. You will want to save this somewhere (will be used in the locust section too).

Note: If you get an error during this step saying that you need a public DID, go follow the previous instructions again (or, alternatively, analyze your process --- something may be going wrong when anchoring your DID).

#### Creating a Credential Definition

Now that we have a schema created, let's scroll up to the section titled `credential-defintiion`. Click on the $\color{green}{post}$ method titled $\color{green}{/credential-definitions}$ and, again, click on the `Try it out` button. Modify the `body` JSON values so it looks like

```
{
  "schema_id": "pasteSchemaIDHere",
  "support_revocation": false,
  "tag": "default"
}
```

where `pasteSchemaIDHere` is the `schema_id` you just copied in the previous step. We will not be concerning ourselves with revocation at the moment but, certainly, we can in the future. If you've confirmed your JSON body value follows a similar format, go ahead and click the blue $\color{blue}{Execute}$ button. Again, as you copied the DID and `schema_id` from before, go ahead and copy this top `credential_definition_id`. Once again, we will be using this later, so make sure to save it some place safe.

Awesome trooper! Now we're ready to move onto locust!

## Locust

Now we arm our soliders for battle. In order to do this, we need to arm our troops with armor and weapons! To do this, we need to prepare our VMs a little bit more, rather than cloning down the respective repo immediately.

Here is a script for setting up a new VM to run Locust.

```
sudo echo '{
  "log-driver": "json-file",
  "log-opts": {"max-size": "10m", "max-file": "3"}
}' >> /etc/docker/daemon.json

# Add swap file to add reliability to memory management...
sudo dd if=/dev/zero of=/swap bs=1M count=512
sudo chmod 0600 /swap
sudo mkswap /swap
sudo echo "/swap swap      swap    defaults        0 2" >> /etc/fstab

sudo reboot
```

After executing these commands, you'll need to SSH into this locust VM again.

For this prepatory portion of the adventure, we will once again need that same repo from earlier.

We can do this by cloning down the [aries-akrida](https://github.com/Indicio-tech/aries-akrida) repository. Do so, by doing

```
git clone git@github.com:Indicio-tech/aries-akrida.git
```

Go ahead and navigate into this repo by doing `cd aries-akrida`.
Before we go ahead and populate our `.env` file, we'll need to locally clone down a specific version for AFJ for our clients. (For motiviation on why we're doing this, see our design document. :) We use AFJ to simulate our clients here.) If you haven't already, `cd aries-akrida`.

```
# A specific fork of AFJ is currently used to support listening to trustping events. This pull request was added to AFJ, and future versions may use the standard AFJ package.
git clone https://github.com/reflectivedevelopment/aries-framework-javascript.git
cd aries-framework-javascript
git checkout feature/add_trustping_events
cd ../
```

Now we'll take care of populating the `.env` file. However, we will need some information from AWS in order to fill it out.

Besides AWS, if you have your own mediator, this would be the time to populate the `.env` with your mediation url. It's also important, at this step, to know whether it supports version 2 of the pickup protocol (recommended to ask, or just wait for errors to pop up).

For whatever URL you use, please make sure you have permission to use it.

For now, let us return our attention back to the browser. Navigate back to the `Instances > Instances` area. As previously, we will want to record

- the `internal / private IP` of the `locust` VM,
- the `external / public IP` of the `locust` VM, and
- the `external / public IP` of the `ACA-Py Agent` VM.

You can find each of these by clicking on the `Instance ID` of each of the respective VMs, as before. After collecting these, please proceed to populating the `.env`.

### Populating .env (ACA-Py Agent)

This environment will need to be populated every time you spin up and down the environment (namely, the postgres db and ACA-Py agent).

The best way to modify this will probably be via an in-line text editor (we'll use `vim` here but feel free to choose whatever you like best).

_(If you're uncomfortable with in-line text editors, it would be best to copy the whole test, edit however you best see fit, and then $\text{(a)}$ open the file with `vim .env`, $\text{(b)}$ paste in all of the copied text by doing into insert mode with `i` and pressing `Ctrl + V` or `Command + V`, $\text{(c)}$ pressing the `Escape` button, and then $\text{(d)}$ typing in `:wq`.)_

```
MEDIATION_URL=<Insert mediation URL here>

# Period an agent will wait before running another ping
LOCUST_MIN_WAIT=1
LOCUST_MAX_WAIT=10

AGENT_IP=# Internal IP locust VM
MASTER_HOST=# External IP locust VM
MASTER_PORT=8089

# Begins with http://, ends in :8150
ISSUER_URL=http://{EXTERNAL_IP_OF_ACAPY_AGENT}:8150
ISSUER_HEADERS={"Authorization":"Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiIwOWY5ZDAwNC02OTM0LTQyZDYtOGI4NC1jZTY4YmViYzRjYTUiLCJpYXQiOjE2NzY4NDExMTB9.pDQPjiYEAoDJf3044zbsHrSjijgS-yC8t-9ZiuC08x8"}

# Ledger of choice (candy, etc.)
LEDGER=indicio

CRED_DEF= # Credential definition from earlier
CRED_ATTR='[{"mime-type": "text/plain","name": "score","value": "test"}]'
SCHEMA= # Schema from earlier
VERIFIED_TIMEOUT_SECONDS=20

# Simple arbitrary 3 issuances per 1 verification scenario for now
LOCUST_FILES=locustFractionMediatorIssueVerify.py

# Increase the END_PORT if you want to run a lot of agents in parallel
START_PORT=10000
END_PORT=12000
```

(Optional) Additionally, if you would like to send a 1KB message over mediation, here is a sample 1KB message that you're welcome to populate within your .env file.

```
MESSAGE_TO_SEND="Amidst the tranquil embrace of nature, where the sun's golden rays paint the sky with hues of warmth, and the gentle rustle of leaves creates a symphony of serenity, I find solace. In this haven of stillness, worries dissipate like morning mist, and the heart finds a rhythm in harmony with the earth's pulse. It's a reminder that amidst the chaos of life, there exists a tranquil sanctuary within us, waiting to be discovered. As we journey through the tapestry of existence, may we always take a moment to bask in the simple beauty that surrounds us. Amidst the tranquil embrace of nature, where the sun's golden rays paint the sky with hues of warmth, and the gentle rustle of leaves creates a symphony of serenity, I find solace. In this haven of stillness, worries dissipate like morning mist, and the heart finds a rhythm in harmony with the earth's pulse. It's a reminder that amidst the chaos of life, there exists a tranquil sanctuary within us, waiting to be discovered. As we journey through the tapestry of existence"
```

And, that's it! Last, but not least, we'll go ahead and adjust the firewall rules.

### Firewall Rules (Locust)

For locust, [if you investigate the `docker-compose.yml`] we will need to allow traffic in on ports `8089` and `8090`, as well as all of the ports you would like to expose for the agents (by default, we put in ports `10000-12000`). The amount of ports that you can actually use [for users] will be resource constricted, which we will touch on later (in the clustered portion). Additionally, in order to be able to communicate with the `ACA-Py` agent for issuance scenarios, we will need to allow traffic in on that machine [the ACA-Py Agent VM] on port `3000`.

For now, as before, add these firewall rules

1. Allow yourself access to `8089-8090`
   - Type: `Custom TCP`
   - Port Range: `8089-8090`
   - Source: `My Ip`
2. Allow Locust access to the ACA-Py Admin UI (`8150-8151`)
   - Type: `Custom TCP`
   - Port Range: `8150-8151`
   - Source: `Custom TCP`
     - `Locust Exteral IP` / 32
3. (We are pretty liberal here for these smaller clients) Allow all access to ports `10000-12000`
   - Type: `Custom TCP`
   - Port Range: `6379`
   - Source: `Anywhere IPv4`
     - `0.0.0.0/0`

Awesome! From here, we should be good to go, if you have already populated the `.env`. To proceed, just type in

```
sudo docker-compose build
sudo docker-compose up
```

Once everything spins up, the locust browser will be available on `http://{EXTERNAL_IP_OF_LOCUST_VM}:8089`. Go ahead and give things a whirl with `1` total user spawning at a rate of `1` per second. It might take a moment to go through all of the scenarios but, if things are successful, then you've successfully spun up the environment!

For now, please don't go more aggressive than this (unless you chose, at the offset, a sufficiently powerful VM). (Going aggressive will put the machine in a funky state and just be a nuissance, but, by all means...) We will provide documentation on this bit later. Otherwise, we hope this helped! :) This is how to get your locust framework up and running, in a non-clustered environment.

Below, we will provide documentation on how to up your environment if you want to use your own mediator [and how to spin that up].

### Resolving Pickup Protocol Versions

If the mediator you are using does not support version 2 of the pickup protocol, make sure to comment out line 45 of `load-agent/agent.js`; that is,

```
mediatorPickupStrategy: ariesCore.MediatorPickupStrategy.PickUpV2
```

Then down, rebuild, and up the locust VM again.

### Resolving Docker Port Issues / "Hanging" Docker

Sometimes, after you have entirely spun down the environment and are trying to up everything again, docker will want to use up all of the ports you have exposed. To prevent this from happening (when this happens, all `docker` commands will appear to be entirely unresponsive (aka just hang when you type a command)), here are some helpful commands:

```
# (Optionally) pkill -9 -f docker
sudo systemctl disable docker docker.socket
# Recommend to stop + start through AWS, not here
sudo reboot
# When you SSH back in:
sudo rm -rf /var/lib/docker
```

## Mediator

This last part is optional, only if you want to up your own mediator. We will proceed with either the assumption that you (a) have permissions to set DNS entries (for Amazon, via Route 53) or (b) will be able to ask for this.

To begin, clone down the [aries-akrida](https://github.com/Indicio-tech/aries-akrida) repository. Do so, by doing

```
git clone git@github.com:Indicio-tech/aries-akrida.git
```

Go ahead and navigate into this repo by doing `cd aries-akrida`. From there, we will want to take all of the relevant files we will need (without really needing the rest). We can do that by

```
cd instance-configs/mediator
mv * ../../../
cd ../../../
rm -rf aries-akrida/
```

so that we are only left with the relevant files in the mediator directory for this VM. In order to proceed with setting everything up, we will need to have a permanent, public IP address for this mediator VM.

### Persistent Public IP

In order to do this, head back to the browser with AWS. Click the menu on the left-hand side and navigate to `Network & Security > Elastic IPs`.

Click the orange `Allocate Elastic IP address` button. Ensure the border group is within the same region you have put all of your previous VMs.

Under the section `Tags - optional`, we recommend giving this IP you're allocating a name. Do this by going to `Key` and typing in `Name`. For `Value - optional`, type in what you would like to name this. Perhaps, `mediator` or `local-mediator`? Then, click the orange `Allocate` button.

Once it brings you back to the menu of that section, click on the top `Actions` dropdown, and then press `Associate Elastic IP address`.

Under `Resource type`, ensure `Instance` is selected. Under `Instance`, choose the instance of the mediator VM. If you would like, you can also ask for this Elastic IP address to be reassociated. (i.e. if you accidentally press "Terminate Instance" instead of "Stop Instance" at the end of the day, this might save you some hassle) (whoops).

Go ahead and press the orange `Associate` button.

Awesome! You've now associated the public IP address with the mediator VM permanently to this specific instance!

At this time, this would be a good time to ask your higher ups to reserve some sort useful, appropriate DNS name to this public IP.

From there, we will need to populate the `.env` file, as we did previously. (`cd aries-akrida/` if you haven't already.)

The best way to modify this will probably be via an in-line text editor (we'll use `vim` here but feel free to choose whatever you like best).

_(If you're uncomfortable with in-line text editors, it would be best to copy the whole test, edit however you best see fit, and then $\text{(a)}$ open the file with `vim .env`, $\text{(b)}$ paste in all of the copied text by doing into insert mode with `i` and pressing `Ctrl + V` or `Command + V`, $\text{(c)}$ pressing the `Escape` button, and then $\text{(d)}$ typing in `:wq`.)_

```
MEDIATOR_CONTROLLER_ADMIN_API_KEY=insecure-hello-world-1
MEDIATOR_AGENT_ADMIN_API_KEY=insecure-hello-world-2
MEDIATOR_ALIAS=MOON
#LOG_LEVEL=INFO
MEDIATOR_URL= # Put your DNS Entry Here
POSTGRESQL_HOST=db
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=acapy
POSTGRESQL_ADMIN_USER=postgres
POSTGRESQL_ADMIN_PASSWORD=acapy
MEDIATOR_WALLET_NAME=mediator
MEDIATOR_WALLET_KEY=testing
```

After filling out the `.env`, we can go ahead and fill out our usual firewall rules

### Firewall Rules (Mediator)

For now, as before, add these firewall rules

1. Allow locust to access this mediator on port `3000`
   - Type: `Custom TCP`
   - Port Range: `3000`
   - Source: `Custom TCP`
     - `Locust External IP` / 32
2. Allow the mediator to be able to access itself with its external IP on port `3000`
   - Type: `Custom TCP`
   - Port Range: `3000`
   - Source: `Custom TCP`
     - `Mediator External IP` / 32
3. Allow the mediator to be able to access locust on ports `8089-8090`
   - Type: `Custom TCP`
   - Port Range: `8089-8090`
   - Source: `Custom TCP`
     - `Mediator External IP` /32
4. Allow the mediator to be able to access the ACA-Py agent on ports `8150-8151`
   - Type: `Custom TCP`
   - Port Range: `8089-8090`
   - Source: `Custom TCP`
     - `Mediator External IP` / 32

Awesome! From here, we should be good to go, if you have already populated the `.env`. To proceed, just type in

```
sudo docker build -f Dockerfile --no-cache -t indicio-tech/aries-mediator .
sudo docker-compose up
```

The output, when finally upping this mediator, will result in a `MEDIATION_URL`. You will want to copy this, and use this in the `.env` of the locust VM. Additionally, this mediator does not support version two of the pickup protocol, so make sure to comment out line 45 of `load-agent/agent.js`; that is,

```
mediatorPickupStrategy: ariesCore.MediatorPickupStrategy.PickUpV2
```

Then down, rebuild, and up the locust VM again.

---

### Optional: Extra Directions for Certificates

Additionally, if it is helpful, here's some commands as to how we got the certificate to work (using nginx) on google cloud:

```
# Reserve DNS name within Cloud DNS, or whichever cloud provider you are using (still need static IP)
sudo apt update
sudo apt install certbot
# sudo add-apt-repository ppa:certbot/certbot
# sudo apt install python3-certbot-nginx
sudo certbot --nginx -d insert_DNS_Name_Here
```

In doing things this way, you'll also have to stop nginx on port 80, but this should also work if the above section doesn't.

---

Don't forget, once you're done with everything, to go back to the `Instances > Instances` panel, select all of your instanes, click on the box on the top right titled `Instance State`, and press `Stop instance` once you are done :) To start up the environment, on the other hand, select those instances and press `Start instance`. Don't forget, when you start back up the instances, you'll need to clear out the database VM by doing

```
sudo rm -rf holder-db/ redis*
sudo docker-compose down -v && sudo docker-compose build && sudo docker-compose up
```

Additionally, on this note you'll also have to down, build, up, and re-anchor everything for the ACA-Py agent VM.

---

## Common Issues

There are a myriad of issues you can encounter while setting up the environment. Below, we'll document some well-known ones we have fixes for. Let live as a living document, so common issues can be updated down below as the community grows and more issues are known.

#### Incorrect Service Endpoint; Changing Exposed Port in `docker-compose.yml`

This one will result in an error within locust. Observe the service endpoint of the returned failure.

If you're using a non-clustered environment, this should be set to the port`8150`. If you're using a clustered environment, this should be the transport port of your load balancer.

If the port is incorrect, SSH into your `ACA-Py` agent VM and change the one line in the `docker-compose.yml` that is wrong. (There will only be one.)

Unfortunately, after this, down, rebuild, up, and reanchor everything for the ACA-Py VM. Further, propagate these changes to the locust agent, down, and up the locust agent again.
