// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// Vickrey auction contract
contract EnergyVickreyAuction {
    struct Bid {
        bytes32 sealedBid;
        uint256 deposit; // Amount sent with the bid transaction
    }

    address public seller;
    uint256 public biddingStart;
    uint256 public biddingEnd;
    uint256 public revealEnd;
    bool public ended; // Tracks if the auction has been finalized by closeAuction
    uint256 public biddingDuration; // Can be updated by resetAuction
    uint256 public revealDuration;  // Can be updated by resetAuction

    mapping(address => Bid) public bids;
    address[] public bidders; // Keep track of who placed a bid

    address public highestBidder;
    uint256 public highestBid;     // Highest revealed value
    uint256 public secondHighestBid; // Second highest revealed value

    uint256 public energyAmount; // Amount of energy being auctioned in the current/last round

    // --- Events ---
    event AuctionStarted(address indexed seller, uint256 energyAmount, uint256 biddingEnd, uint256 revealEnd);
    event BidPlaced(address indexed bidder, uint256 deposit);
    event BidRevealed(address indexed bidder, uint256 value);
    event AuctionClosed(address winner, uint256 winningPrice, uint256 energyAmount);
    event AuctionReset(uint256 newBiddingDuration, uint256 newRevealDuration); // Modified event

    // --- Modifiers ---
    modifier onlyBefore(uint256 _time) {
        require(block.timestamp < _time, "Auction phase has ended");
        _;
    }

    modifier onlyAfter(uint256 _time) {
        require(block.timestamp >= _time, "Auction phase has not started yet");
        _;
    }

    modifier auctionNotClosed() {
        // Checks if closeAuction has been called for the *current* active round
        require(!ended, "Auction already closed");
        _;
    }

     modifier auctionIsClosed() {
        // Checks if closeAuction has been called, required for reset/start
        require(ended, "Auction must be closed first");
        _;
    }

    modifier onlySeller() {
        require(msg.sender == seller, "Only the current seller can perform this action");
        _;
    }

    // --- Constructor ---
    constructor(uint256 _biddingDuration, uint256 _revealDuration) {
        seller = msg.sender; // Initial seller is deployer
        biddingDuration = _biddingDuration;
        revealDuration = _revealDuration;
        biddingStart = 0; // No auction active initially
        ended = true; // Start in an ended state, requiring startAuction or reset followed by startAuction
    }

    // --- Read Functions ---
    function getBidders() external view returns (address[] memory) {
        return bidders;
    }

    function getBidDeposits() external view returns (address[] memory, uint256[] memory) {
        if (bidders.length == 0) {
            address[] memory emptyAddresses = new address[](0);
            uint256[] memory emptyUints = new uint256[](0);
            return (emptyAddresses, emptyUints);
        }
        uint256[] memory deposits = new uint256[](bidders.length);
        for (uint256 i = 0; i < bidders.length; i++) {
            deposits[i] = bids[bidders[i]].deposit;
        }
        return (bidders, deposits);
    }

    // --- State Changing Functions ---

    // Start a new auction round (can only be called after closeAuction or resetAuction)
    function startAuction(uint256 _energyAmount) external auctionIsClosed {
        // Reset core state variables for a new round
        // Note: bidders array and bids mapping entries are effectively cleared
        // by not carrying them over and by overwriting bids on new bid() calls.
        delete bidders; // Clear the array of bidders from the previous round
        highestBidder = address(0);
        highestBid = 0;
        secondHighestBid = 0;

        // Set new auction parameters
        seller = msg.sender; // The caller of startAuction becomes the seller for this round
        energyAmount = _energyAmount;
        biddingStart = block.timestamp; // Mark the start time
        // Use durations currently set (could have been changed by resetAuction)
        biddingEnd = biddingStart + biddingDuration;
        revealEnd = biddingEnd + revealDuration;
        ended = false; // Mark the auction as active

        emit AuctionStarted(seller, energyAmount, biddingEnd, revealEnd);
    }

    // Place a sealed bid during the bidding phase
    function bid(bytes32 _sealedBid)
        external
        payable
        onlyAfter(biddingStart)
        onlyBefore(biddingEnd)
        auctionNotClosed
    {
        // Prevent bidder from bidding twice in the same round
        require(bids[msg.sender].sealedBid == bytes32(0) || bids[msg.sender].deposit == 0, "Bidder has already placed a bid this round");
        require(msg.value > 0, "Deposit must be greater than 0");

        // If bidder existed before, overwrite; otherwise, add new entry
        bool bidderExists = false;
        for(uint i=0; i<bidders.length; i++){
            if(bidders[i] == msg.sender){
                bidderExists = true;
                break;
            }
        }
        if(!bidderExists){
             bidders.push(msg.sender); // Add bidder only if they aren't already in the list for this round
        }

        bids[msg.sender] = Bid({
            sealedBid: _sealedBid,
            deposit: msg.value
        });


        emit BidPlaced(msg.sender, msg.value);
    }

    // Reveal the actual bid value during the reveal phase
    function reveal(uint256 _value, string calldata _nonce)
        external
        onlyAfter(biddingEnd)
        onlyBefore(revealEnd)
        auctionNotClosed
    {
        Bid storage bidToCheck = bids[msg.sender];
        require(bidToCheck.sealedBid != bytes32(0), "No unrevealed bid found for this address");

        require(
            bidToCheck.sealedBid == keccak256(abi.encodePacked(_value, _nonce)),
            "Invalid bid reveal: Hash mismatch"
        );
        require(bidToCheck.deposit >= _value, "Deposit is less than revealed bid value");

        if (_value > highestBid) {
            secondHighestBid = highestBid;
            highestBid = _value;
            highestBidder = msg.sender;
        } else if (_value > secondHighestBid) {
            secondHighestBid = _value;
        }

        // Mark bid as revealed by clearing sealedBid (prevents double reveal)
        bidToCheck.sealedBid = bytes32(0);

        emit BidRevealed(msg.sender, _value);
    }

    // Finalize the auction after the reveal phase ends
    function closeAuction()
        external
        onlyAfter(revealEnd)
        auctionNotClosed
    {
        ended = true; // Mark auction as closed

        address winner = highestBidder;
        uint256 winningPrice = secondHighestBid;

        if (winner != address(0)) {
            // Pay seller
            (bool successSeller, ) = payable(seller).call{value: winningPrice}("");
            require(successSeller, "Seller payment failed");

            // Refund winner (deposit - winning price)
            uint256 winnerDeposit = bids[winner].deposit;
            if (winnerDeposit > winningPrice) {
                uint256 winnerRefund = winnerDeposit - winningPrice;
                // Clear deposit *before* sending refund (Checks-Effects-Interactions pattern)
                bids[winner].deposit = 0;
                (bool successWinner, ) = payable(winner).call{value: winnerRefund}("");
                require(successWinner, "Winner refund failed");
            } else {
                // If deposit <= winningPrice (should only be == if check in reveal is correct)
                bids[winner].deposit = 0; // Clear deposit even if no refund needed
                if(winnerDeposit < winningPrice) {
                     revert("Winner deposit insufficient for winning price (Internal Error)");
                }
            }
        } else {
             winningPrice = 0;
        }

        // Refund non-winners
        for (uint256 i = 0; i < bidders.length; i++) {
            address bidder = bidders[i];
            if (bidder != winner && bids[bidder].deposit > 0) {
                uint256 refundAmount = bids[bidder].deposit;
                bids[bidder].deposit = 0; // Clear deposit before transfer
                (bool successRefund, ) = payable(bidder).call{value: refundAmount}("");
                require(successRefund, "Non-winner refund failed");
            }
        }

        emit AuctionClosed(winner, winningPrice, energyAmount);

        // Explicitly reset biddingStart to allow startAuction again
        // Although startAuction checks 'ended', this provides clarity
        biddingStart = 0;
    }

    // Reset auction parameters (can be called only by the seller of the *last* round)
    function resetAuction(uint256 _newBiddingDuration, uint256 _newRevealDuration)
        external
        onlySeller // Only the seller of the last round can reset parameters
        auctionIsClosed // Can only reset after the last round was closed
    {
        // Update the durations for the *next* round
        biddingDuration = _newBiddingDuration;
        revealDuration = _newRevealDuration;

        // Resetting state variables is primarily handled by startAuction now.
        // This function focuses only on updating durations and ensuring the state
        // is ready for a *future* startAuction call.
        // Ensure biddingStart remains 0 if it was already set by closeAuction.
        if(biddingStart != 0) {
             biddingStart = 0;
        }
        // ended should already be true due to auctionIsClosed modifier

        // Clear previous round's winner/bid info if not already cleared by startAuction logic
        highestBidder = address(0);
        highestBid = 0;
        secondHighestBid = 0;
        delete bidders; // Ensure bidders array is clear

        // Note: We don't necessarily need to delete the 'bids' mapping here,
        // as startAuction doesn't rely on it being empty, and bid() overwrites.

        emit AuctionReset(_newBiddingDuration, _newRevealDuration);
    }
}