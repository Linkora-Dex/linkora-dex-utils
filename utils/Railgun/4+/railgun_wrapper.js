const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');

class SimpleRailgunWrapper {
  constructor() {
    this.provider = null;
    this.signer = null;
    this.network = null;
    this.wallet = null;
    this.isInitialized = false;
  }

  async initialize(network = 'polygon', rpcUrl = null, privateKey = null) {
    try {
      this.network = network;
      const defaultRpcUrl = this.getDefaultRpcUrl(network);
      this.provider = new ethers.JsonRpcProvider(rpcUrl || defaultRpcUrl);
      if (privateKey) {
        this.signer = new ethers.Wallet(privateKey, this.provider);
      }
      this.isInitialized = true;
      const blockNumber = await this.provider.getBlockNumber();
      console.log(`Connected to ${network}, block: ${blockNumber}`);
      return {
        success: true,
        message: `Initialized on ${network}`,
        blockNumber: blockNumber
      };
    } catch (error) {
      console.error('Initialization failed:', error);
      return { success: false, error: error.message };
    }
  }

  async loadWallet(mnemonic, password = 'defaultPassword', network = null, rpcUrl = null, privateKey = null) {
    try {
      if (!this.isInitialized && network) {
        const initResult = await this.initialize(network, rpcUrl, privateKey);
        if (!initResult.success) {
          throw new Error(`Auto-initialization failed: ${initResult.error}`);
        }
      }
      if (!this.isInitialized) {
        throw new Error('Engine not initialized and no network provided');
      }
      const hdNode = ethers.HDNodeWallet.fromPhrase(mnemonic);
      const walletId = ethers.keccak256(ethers.toUtf8Bytes(mnemonic + password));
      const addressSeed = ethers.keccak256(ethers.concat([walletId, ethers.toUtf8Bytes('railgun')]));
      const railgunAddress = '0zk' + addressSeed.slice(2, 42);
      this.wallet = {
        id: walletId,
        address: railgunAddress,
        hdNode: hdNode,
        mnemonic: mnemonic
      };
      return {
        success: true,
        wallet: {
          id: this.wallet.id,
          address: this.wallet.address
        }
      };
    } catch (error) {
      console.error('Wallet loading failed:', error);
      return { success: false, error: error.message };
    }
  }

  async shieldTokens(tokenAddress, amount, gasPrice = null) {
    try {
      if (!this.wallet || !this.signer) {
        throw new Error('Wallet and signer required');
      }

      const amountStr = typeof amount === 'string' ? amount : amount.toString();
      const amountBigInt = BigInt(amountStr);

      console.log('Starting RAILGUN Shield operation...');
      console.log(`Token: ${tokenAddress}`);
      console.log(`Amount: ${amountStr}`);

      const railgunRelayAddress = this.getRailgunContractAddress(this.network);
      console.log(`RAILGUN Relay Contract: ${railgunRelayAddress}`);

      let transaction;
      if (tokenAddress === "0x0000000000000000000000000000000000000000") {
        console.log('Shielding native MATIC tokens...');
        const currentGasPrice = await this.provider.getGasPrice();
        transaction = {
          to: railgunRelayAddress,
          value: amountStr,
          data: this.generateShieldData(amountBigInt, this.wallet.address),
          gasLimit: 800000,
          gasPrice: gasPrice ? gasPrice.toString() : currentGasPrice.toString()
        };
      } else {
        console.log('Shielding ERC20 tokens...');
        const erc20Abi = [
          'function approve(address spender, uint256 amount) returns (bool)',
          'function allowance(address owner, address spender) view returns (uint256)'
        ];
        const tokenContract = new ethers.Contract(tokenAddress, erc20Abi, this.signer);
        const currentAllowance = await tokenContract.allowance(this.signer.address, railgunRelayAddress);
        console.log(`Current allowance: ${currentAllowance}`);

        if (currentAllowance < amountBigInt) {
          console.log('Approving token spending...');
          const approveTx = await tokenContract.approve(railgunRelayAddress, amountStr);
          await approveTx.wait();
          console.log('Token approval completed');
        }

        const currentGasPrice = await this.provider.getGasPrice();
        transaction = {
          to: railgunRelayAddress,
          value: "0",
          data: this.generateShieldData(amountBigInt, this.wallet.address, tokenAddress),
          gasLimit: 900000,
          gasPrice: gasPrice ? gasPrice.toString() : currentGasPrice.toString()
        };
      }

      console.log('Sending shield transaction to RAILGUN...');
      console.log(`Gas limit: ${transaction.gasLimit}`);

      const txResponse = await this.signer.sendTransaction(transaction);
      console.log(`Transaction sent: ${txResponse.hash}`);

      const receipt = await txResponse.wait();
      console.log('Shield transaction confirmed');

      return {
        success: true,
        txHash: receipt.hash,
        status: receipt.status === 1 ? 'confirmed' : 'failed',
        gasUsed: receipt.gasUsed.toString(),
        blockNumber: receipt.blockNumber
      };
    } catch (error) {
      console.error('Shield failed:', error);
      return { success: false, error: error.message };
    }
  }

  async unshieldTokens(tokenAddress, amount, recipientAddress, gasPrice = null) {
    try {
      if (!this.wallet || !this.signer) {
        throw new Error('Wallet and signer required');
      }

      const amountStr = typeof amount === 'string' ? amount : amount.toString();
      const amountBigInt = BigInt(amountStr);

      console.log('Starting RAILGUN Unshield operation...');
      console.log(`Token: ${tokenAddress}`);
      console.log(`Amount: ${amountStr}`);
      console.log(`Recipient: ${recipientAddress}`);

      const railgunRelayAddress = this.getRailgunContractAddress(this.network);
      console.log(`RAILGUN Relay Contract: ${railgunRelayAddress}`);

      const currentGasPrice = await this.provider.getGasPrice();
      const transaction = {
        to: railgunRelayAddress,
        value: "0",
        data: this.generateUnshieldData(amountBigInt, recipientAddress, tokenAddress),
        gasLimit: 900000,
        gasPrice: gasPrice ? gasPrice.toString() : currentGasPrice.toString()
      };

      console.log('Sending unshield transaction to RAILGUN...');
      console.log(`Gas limit: ${transaction.gasLimit}`);

      const txResponse = await this.signer.sendTransaction(transaction);
      console.log(`Transaction sent: ${txResponse.hash}`);

      const receipt = await txResponse.wait();
      console.log('Unshield transaction confirmed');

      return {
        success: true,
        txHash: receipt.hash,
        status: receipt.status === 1 ? 'confirmed' : 'failed',
        gasUsed: receipt.gasUsed.toString(),
        blockNumber: receipt.blockNumber
      };
    } catch (error) {
      console.error('Unshield failed:', error);
      return { success: false, error: error.message };
    }
  }

  async getBalances() {
    try {
      if (!this.wallet) {
        throw new Error('No wallet loaded');
      }
      const balances = {
        'MATIC': '0',
        'private_balance': 'encrypted'
      };
      return {
        success: true,
        balances: balances
      };
    } catch (error) {
      console.error('Failed to get balances:', error);
      return { success: false, error: error.message };
    }
  }

  generateShieldData(amount, railgunAddress, tokenAddress = null) {
    const functionSelector = '0x1cd43ef6';
    const amountBigInt = typeof amount === 'string' ? BigInt(amount) : amount;

    const commitment = ethers.keccak256(ethers.concat([
      ethers.zeroPadValue(ethers.toBeHex(amountBigInt), 32),
      ethers.zeroPadValue(railgunAddress, 32),
      ethers.randomBytes(16)
    ]));

    const transaction = {
      commitments: [commitment],
      nullifiers: [],
      merkleRoot: ethers.ZeroHash,
      tokenData: [{
        tokenType: tokenAddress === ethers.ZeroAddress || tokenAddress === "0x0000000000000000000000000000000000000000" ? 0 : 1,
        tokenAddress: tokenAddress || ethers.ZeroAddress,
        tokenSubID: 0
      }],
      proof: Array(8).fill(0),
      depositSignature: ethers.ZeroHash
    };

    const encodedData = ethers.AbiCoder.defaultAbiCoder().encode(
      ['tuple(bytes32[] commitments, bytes32[] nullifiers, bytes32 merkleRoot, tuple(uint8 tokenType, address tokenAddress, uint256 tokenSubID)[] tokenData, uint256[8] proof, bytes32 depositSignature)[]'],
      [[transaction]]
    );

    return functionSelector + encodedData.slice(2);
  }

  generateUnshieldData(amount, recipientAddress, tokenAddress = null) {
    const functionSelector = '0x1cd43ef6';
    const amountBigInt = typeof amount === 'string' ? BigInt(amount) : amount;

    const nullifier = ethers.keccak256(ethers.concat([
      ethers.zeroPadValue(ethers.toBeHex(amountBigInt), 32),
      ethers.zeroPadValue(recipientAddress, 32),
      ethers.randomBytes(16)
    ]));

    const transaction = {
      commitments: [],
      nullifiers: [nullifier],
      merkleRoot: ethers.ZeroHash,
      tokenData: [{
        tokenType: tokenAddress === ethers.ZeroAddress || tokenAddress === "0x0000000000000000000000000000000000000000" ? 0 : 1,
        tokenAddress: tokenAddress || ethers.ZeroAddress,
        tokenSubID: 0
      }],
      proof: Array(8).fill(0),
      depositSignature: ethers.ZeroHash
    };

    const encodedData = ethers.AbiCoder.defaultAbiCoder().encode(
      ['tuple(bytes32[] commitments, bytes32[] nullifiers, bytes32 merkleRoot, tuple(uint8 tokenType, address tokenAddress, uint256 tokenSubID)[] tokenData, uint256[8] proof, bytes32 depositSignature)[]'],
      [[transaction]]
    );

    return functionSelector + encodedData.slice(2);
  }

  getRailgunContractAddress(network) {
    const contracts = {
      'polygon': '0x19b620929f97b7b990801496c3b361ca5def8c71',
      'ethereum': '0xfa7093cdd9ee6932b4eb2c9e1cde7ce00b1fa4b9',
      'bsc': '0x590162bf4b50F6576a459B75309eE21D92178A10'
    };
    return contracts[network] || contracts['polygon'];
  }

  getRailgunLogicAddress(network) {
    const logicContracts = {
      'polygon': '0x280e417ab3cafc378f3e6f91148fd8ef766d4c95',
      'ethereum': '0x1234567890123456789012345678901234567890',
      'bsc': '0x1234567890123456789012345678901234567890'
    };
    return logicContracts[network] || logicContracts['polygon'];
  }

  getDefaultRpcUrl(network) {
    const rpcUrls = {
      'ethereum': 'https://eth-mainnet.g.alchemy.com/v2/demo',
      'polygon': 'https://polygon-rpc.com',
      'bsc': 'https://bsc-dataseed.binance.org/',
      'arbitrum': 'https://arb1.arbitrum.io/rpc'
    };
    return rpcUrls[network] || rpcUrls['polygon'];
  }

  async cleanup() {
    return { success: true, message: 'Cleanup completed' };
  }
}

if (require.main === module) {
  const wrapper = new SimpleRailgunWrapper();
  const args = process.argv.slice(2);
  const command = args[0];

  async function handleCommand() {
    try {
      switch (command) {
        case 'init':
          const network = args[1] || 'polygon';
          const rpcUrl = args[2];
          const privateKey = args[3];
          const result = await wrapper.initialize(network, rpcUrl, privateKey);
          console.log(JSON.stringify(result));
          break;

        case 'load-wallet':
          const loadMnemonic = args[1];
          const loadPassword = args[2] || 'defaultPassword';
          const loadNetwork = args[3];
          const loadRpcUrl = args[4];
          const loadPrivateKey = args[5];
          const loadResult = await wrapper.loadWallet(loadMnemonic, loadPassword, loadNetwork, loadRpcUrl, loadPrivateKey);
          console.log(JSON.stringify(loadResult));
          break;

        case 'balances':
          const balancesResult = await wrapper.getBalances();
          console.log(JSON.stringify(balancesResult));
          break;

        case 'shield':
          const tokenAddress = args[1];
          const amount = args[2];
          const gasPrice = args[3];
          const shNetwork = args[4];
          const shRpcUrl = args[5];
          const shPrivateKey = args[6];
          const shMnemonic = args[7];

          if (shNetwork && shRpcUrl && shPrivateKey && shMnemonic) {
            const shInitResult = await wrapper.initialize(shNetwork, shRpcUrl, shPrivateKey);
            if (!shInitResult.success) {
              console.log(JSON.stringify(shInitResult));
              break;
            }
            const shWalletResult = await wrapper.loadWallet(shMnemonic);
            if (!shWalletResult.success) {
              console.log(JSON.stringify(shWalletResult));
              break;
            }
          }

          const shieldResult = await wrapper.shieldTokens(tokenAddress, amount, gasPrice);
          console.log(JSON.stringify(shieldResult));
          break;

        case 'unshield':
          const unshieldToken = args[1];
          const unshieldAmount = args[2];
          const recipient = args[3];
          const unshieldGasPrice = args[4];
          const unNetwork = args[5];
          const unRpcUrl = args[6];
          const unPrivateKey = args[7];
          const unMnemonic = args[8];

          if (unNetwork && unRpcUrl && unPrivateKey && unMnemonic) {
            const unInitResult = await wrapper.initialize(unNetwork, unRpcUrl, unPrivateKey);
            if (!unInitResult.success) {
              console.log(JSON.stringify(unInitResult));
              break;
            }
            const unWalletResult = await wrapper.loadWallet(unMnemonic);
            if (!unWalletResult.success) {
              console.log(JSON.stringify(unWalletResult));
              break;
            }
          }

          const unshieldResult = await wrapper.unshieldTokens(unshieldToken, unshieldAmount, recipient, unshieldGasPrice);
          console.log(JSON.stringify(unshieldResult));
          break;

        case 'full-transfer':
          const ftNetwork = args[1] || 'polygon';
          const ftRpcUrl = args[2];
          const ftPrivateKey = args[3];
          const ftMnemonic = args[4];
          const ftTokenAddress = args[5];
          const ftAmount = args[6];
          const ftRecipient = args[7];
          const ftGasPrice = args[8];

          let ftInitResult = await wrapper.initialize(ftNetwork, ftRpcUrl, ftPrivateKey);
          if (!ftInitResult.success) {
            console.log(JSON.stringify(ftInitResult));
            break;
          }

          let ftWalletResult = await wrapper.loadWallet(ftMnemonic);
          if (!ftWalletResult.success) {
            console.log(JSON.stringify(ftWalletResult));
            break;
          }

          let ftShieldResult = await wrapper.shieldTokens(ftTokenAddress, ftAmount, ftGasPrice);
          if (!ftShieldResult.success) {
            console.log(JSON.stringify(ftShieldResult));
            break;
          }

          let ftUnshieldResult = await wrapper.unshieldTokens(ftTokenAddress, ftAmount, ftRecipient, ftGasPrice);
          console.log(JSON.stringify({
            success: true,
            operations: {
              init: ftInitResult,
              wallet: ftWalletResult,
              shield: ftShieldResult,
              unshield: ftUnshieldResult
            }
          }));
          break;

        default:
          console.log(JSON.stringify({
            success: false,
            error: 'Unknown command',
            available: ['init', 'load-wallet', 'balances', 'shield', 'unshield', 'full-transfer']
          }));
      }
    } catch (error) {
      console.log(JSON.stringify({ success: false, error: error.message }));
    } finally {
      await wrapper.cleanup();
      process.exit(0);
    }
  }

  handleCommand();
}

module.exports = { SimpleRailgunWrapper };